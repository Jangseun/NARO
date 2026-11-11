# vision.py
# 카메라 영상 획득 + 얼굴 검출 + 고개 방향/자세 분석을 담당하는 파일
#
# 전체 흐름
#   1) 카메라(Raspberry Pi Camera 또는 USB 웹캠)에서 영상 프레임을 계속 읽는다
#   2) YuNet 얼굴 검출 모델로 얼굴 위치와 5개 특징점(두 눈, 코끝, 입 양 끝)을 찾는다
#   3) 특징점들의 위치 관계로 고개 좌우 회전, 기울기, 상하 방향, 화면 위치, 거리를 계산한다
#   4) 면접 중에는 매 프레임 분석 결과를 모아 두었다가, 질문이 끝나면 통계로 요약한다
#
# 주의: 얼굴 특징점으로 계산한 '고개 방향'이며, 눈동자를 추적하는 시선 추적이 아니다.

import math
import os
import threading
import time

import cv2
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "face_detection_yunet_2023mar.onnx")

# 카메라 해상도 (라즈베리파이에서 느리면 320x240으로 낮춘다)
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 판단 기준값 (실험으로 정한 값이며 필요하면 조정할 수 있다)
YAW_LIMIT = 20         # 좌우 회전이 20도 이내면 '정면'
PITCH_LOW = 0.35       # 상하 지수가 이 값보다 작으면 '고개를 듦'
PITCH_HIGH = 0.75      # 상하 지수가 이 값보다 크면 '고개를 숙임'
ROLL_LIMIT = 10        # 좌우 기울기가 10도를 넘으면 '고개가 기울어짐'
CENTER_LIMIT = 0.15    # 얼굴 중심이 화면 중심에서 15% 이내면 '중앙'
FACE_SIZE_MIN = 0.15   # 얼굴 너비가 화면의 15%보다 작으면 '너무 멂'
FACE_SIZE_MAX = 0.55   # 얼굴 너비가 화면의 55%보다 크면 '너무 가까움'


# ---------------------------------------------------------------------------
# 1. 카메라 영상 획득
# ---------------------------------------------------------------------------

class Camera:
    """Raspberry Pi Camera(picamera) 또는 USB 웹캠(webcam)에서 프레임을 읽는 클래스"""

    def __init__(self, source):
        self.source = source
        self.picam = None
        self.capture = None

        if source == "picamera":
            # 라즈베리파이 OS(Bookworm 이후)의 공식 카메라 라이브러리
            # 라즈베리파이가 아닌 컴퓨터에서는 설치되어 있지 않아 오류가 난다
            from picamera2 import Picamera2
            self.picam = Picamera2()
            # RGB888 형식은 실제로 B, G, R 순서로 저장되어 OpenCV에서 바로 사용할 수 있다
            config = self.picam.create_video_configuration(
                main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"}
            )
            self.picam.configure(config)
            self.picam.start()
            time.sleep(1)  # 카메라 센서가 밝기를 맞출 시간을 준다
        else:
            index = int(os.getenv("WEBCAM_INDEX", "0"))
            if os.name == "nt":
                # 윈도우에서는 DirectShow 방식이 더 빨리 열린다
                self.capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            else:
                self.capture = cv2.VideoCapture(index)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            if not self.capture.isOpened():
                raise RuntimeError(f"웹캠({index}번)을 열 수 없습니다.")

    def read(self):
        """프레임 1장을 BGR 이미지(numpy 배열)로 돌려준다. 실패하면 None"""
        if self.picam is not None:
            frame = self.picam.capture_array()
        else:
            ok, frame = self.capture.read()
            if not ok:
                return None

        # 카메라를 거꾸로 설치한 경우 .env에서 CAMERA_ROTATE_180=1로 설정
        if os.getenv("CAMERA_ROTATE_180") == "1":
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        return frame

    def close(self):
        if self.picam is not None:
            self.picam.stop()
            self.picam.close()
        if self.capture is not None:
            self.capture.release()


# ---------------------------------------------------------------------------
# 2. 얼굴 검출 + 3. 고개 방향/자세 계산
# ---------------------------------------------------------------------------

class FaceAnalyzer:
    """YuNet 모델로 얼굴을 찾고, 특징점으로 고개 방향과 위치를 계산하는 클래스"""

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(f"얼굴 검출 모델 파일이 없습니다: {MODEL_PATH}")
        # 윈도우에서 OpenCV는 한글이 들어간 경로의 파일을 열지 못하므로,
        # 모델 파일을 numpy로 직접 읽어서 메모리(버퍼) 형태로 넘겨준다
        model_data = np.fromfile(MODEL_PATH, dtype=np.uint8)
        empty_config = np.array([], dtype=np.uint8)
        # score_threshold=0.7: 얼굴일 확률이 70% 이상인 것만 얼굴로 인정
        self.detector = cv2.FaceDetectorYN.create(
            "onnx", model_data, empty_config, (FRAME_WIDTH, FRAME_HEIGHT), 0.7
        )

    def analyze(self, frame):
        """프레임 1장을 분석해서 결과를 딕셔너리로 돌려준다"""
        height, width = frame.shape[:2]
        self.detector.setInputSize((width, height))
        _, faces = self.detector.detect(frame)

        if faces is None or len(faces) == 0:
            return {"face_detected": False, "face_count": 0}

        # 얼굴이 여러 개면 가장 큰 얼굴(카메라에 가장 가까운 사람)을 면접자로 본다
        face = max(faces, key=lambda f: f[2] * f[3])

        # YuNet 결과: [x, y, 너비, 높이, 오른눈xy, 왼눈xy, 코끝xy, 입오른쪽xy, 입왼쪽xy, 신뢰도]
        box_x, box_y, box_w, box_h = face[0:4]
        eye_a = np.array(face[4:6])
        eye_b = np.array(face[6:8])
        nose = np.array(face[8:10])
        mouth_a = np.array(face[10:12])
        mouth_b = np.array(face[12:14])
        confidence = float(face[14])

        eye_center = (eye_a + eye_b) / 2
        mouth_center = (mouth_a + mouth_b) / 2
        eye_vector = eye_b - eye_a
        eye_distance = float(np.linalg.norm(eye_vector))
        if eye_distance < 1:
            return {"face_detected": False, "face_count": len(faces)}

        # (1) 기울기(roll): 두 눈을 이은 선이 수평선과 이루는 각도
        roll = math.degrees(math.atan2(eye_vector[1], eye_vector[0]))

        # (2) 좌우 회전(yaw): 코끝이 두 눈의 가운데에서 옆으로 얼마나 벗어났는가
        #     정면이면 코끝이 두 눈 가운데에 있고, 고개를 돌리면 코끝이 한쪽으로 치우친다
        eye_direction = eye_vector / eye_distance
        nose_offset = nose - eye_center
        yaw_ratio = float(np.dot(nose_offset, eye_direction)) / eye_distance
        # 코 높이를 눈 사이 거리의 약 0.6배로 가정한 대략적인 각도 변환
        yaw = math.degrees(math.asin(max(-1.0, min(1.0, yaw_ratio / 0.6))))

        # (3) 상하(pitch) 지수: 눈~입 사이에서 코끝이 어느 높이에 있는가 (0에 가까우면 위, 1에 가까우면 아래)
        #     고개를 숙이면 코끝이 입 쪽으로, 고개를 들면 눈 쪽으로 이동해 보인다
        vertical_direction = np.array([-eye_direction[1], eye_direction[0]])  # 눈 선에 수직인 방향
        eye_to_mouth = float(np.dot(mouth_center - eye_center, vertical_direction))
        eye_to_nose = float(np.dot(nose - eye_center, vertical_direction))
        pitch_ratio = eye_to_nose / eye_to_mouth if eye_to_mouth > 1 else 0.5

        # (4) 화면 위치: 얼굴 중심이 화면 중심에서 얼마나 떨어져 있는가 (-0.5 ~ 0.5)
        face_center_x = float(box_x + box_w / 2) / width
        face_center_y = float(box_y + box_h / 2) / height
        offset_x = face_center_x - 0.5
        offset_y = face_center_y - 0.5

        # (5) 거리: 얼굴 너비가 화면 너비에서 차지하는 비율 (클수록 가까움)
        face_size = float(box_w) / width

        # 각 값을 기준과 비교해서 상태를 판단한다
        facing_front = abs(yaw) <= YAW_LIMIT and PITCH_LOW <= pitch_ratio <= PITCH_HIGH
        head_tilted = abs(roll) > ROLL_LIMIT
        centered = abs(offset_x) <= CENTER_LIMIT and abs(offset_y) <= CENTER_LIMIT + 0.05

        if face_size < FACE_SIZE_MIN:
            distance = "far"
        elif face_size > FACE_SIZE_MAX:
            distance = "close"
        else:
            distance = "good"

        if abs(yaw) > YAW_LIMIT:
            direction = "side"
        elif pitch_ratio < PITCH_LOW:
            direction = "up"
        elif pitch_ratio > PITCH_HIGH:
            direction = "down"
        else:
            direction = "front"

        return {
            "face_detected": True,
            "face_count": len(faces),
            "confidence": round(confidence, 2),
            "yaw": round(yaw, 1),
            "roll": round(roll, 1),
            "pitch_ratio": round(pitch_ratio, 2),
            "offset_x": round(offset_x, 3),
            "offset_y": round(offset_y, 3),
            "face_size": round(face_size, 3),
            "facing_front": facing_front,
            "head_tilted": head_tilted,
            "centered": centered,
            "distance": distance,
            "direction": direction,
            # 화면에 그림을 그리기 위한 좌표 (픽셀)
            "box": [int(box_x), int(box_y), int(box_w), int(box_h)],
            "points": [[int(p[0]), int(p[1])] for p in (eye_a, eye_b, nose, mouth_a, mouth_b)],
        }


def draw_result(frame, result):
    """분석 결과를 영상 위에 그린다 (OpenCV 글꼴은 한글을 지원하지 않아 영어로 표시)"""
    if not result["face_detected"]:
        cv2.putText(frame, "NO FACE", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame

    # 정면이면 초록색, 아니면 주황색
    color = (80, 200, 80) if result["facing_front"] else (0, 140, 255)
    x, y, w, h = result["box"]
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    # 5개 특징점과 두 눈을 잇는 선
    points = result["points"]
    for point in points:
        cv2.circle(frame, tuple(point), 4, (255, 200, 0), -1)
    cv2.line(frame, tuple(points[0]), tuple(points[1]), (255, 200, 0), 1)

    label = f"{result['direction'].upper()}  yaw {result['yaw']:+.0f}  roll {result['roll']:+.0f}"
    cv2.putText(frame, label, (x, max(25, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    # 화면 중앙 십자선 (얼굴을 가운데 맞추는 기준)
    height, width = frame.shape[:2]
    cv2.line(frame, (width // 2 - 15, height // 2), (width // 2 + 15, height // 2), (200, 200, 200), 1)
    cv2.line(frame, (width // 2, height // 2 - 15), (width // 2, height // 2 + 15), (200, 200, 200), 1)
    return frame


# ---------------------------------------------------------------------------
# 4. 면접 중 분석 결과 모으기 + 요약
# ---------------------------------------------------------------------------

def summarize_samples(samples):
    """프레임별 분석 결과 목록을 받아 통계로 요약한다"""
    total = len(samples)
    if total == 0:
        return None

    faces = [s for s in samples if s["face_detected"]]
    face_count = len(faces)
    summary = {
        "total_frames": total,
        "face_detect_ratio": round(face_count / total, 2),
    }
    if face_count == 0:
        summary["posture_score"] = 0
        return summary

    # filter로 조건에 맞는 프레임만 세서 비율을 구한다
    summary["front_ratio"] = round(len([s for s in faces if s["facing_front"]]) / face_count, 2)
    summary["tilt_ratio"] = round(len([s for s in faces if s["head_tilted"]]) / face_count, 2)
    summary["centered_ratio"] = round(len([s for s in faces if s["centered"]]) / face_count, 2)
    summary["down_ratio"] = round(len([s for s in faces if s["direction"] == "down"]) / face_count, 2)
    summary["side_ratio"] = round(len([s for s in faces if s["direction"] == "side"]) / face_count, 2)
    summary["avg_abs_yaw"] = round(sum(abs(s["yaw"]) for s in faces) / face_count, 1)
    summary["avg_abs_roll"] = round(sum(abs(s["roll"]) for s in faces) / face_count, 1)
    summary["avg_face_size"] = round(sum(s["face_size"] for s in faces) / face_count, 3)

    # 움직임: 얼굴 중심 위치가 얼마나 흔들렸는가 (표준편차, 얼굴 크기로 나눠서 거리 영향 제거)
    xs = np.array([s["offset_x"] for s in faces])
    ys = np.array([s["offset_y"] for s in faces])
    movement = (xs.std() + ys.std()) / max(summary["avg_face_size"], 0.01)
    summary["movement"] = round(float(movement), 2)

    # 자세 점수 (100점 만점, 연습용 규칙 기반 점수)
    score = (
        summary["face_detect_ratio"] * 20
        + summary["front_ratio"] * 40
        + (1 - summary["tilt_ratio"]) * 15
        + summary["centered_ratio"] * 15
        + max(0, 1 - summary["movement"] / 0.5) * 10
    )
    summary["posture_score"] = round(score)
    return summary


def make_vision_feedback(summary):
    """요약 통계를 보고 사람이 읽을 수 있는 태도 피드백 문장을 만든다 (규칙 기반)"""
    if summary is None:
        return ["카메라 분석 데이터가 없습니다. 면접 중 카메라를 켜면 자세 분석 결과를 받을 수 있어요."]

    tips = []
    if summary["face_detect_ratio"] < 0.7:
        tips.append(f"얼굴이 인식된 시간이 {summary['face_detect_ratio']:.0%}입니다. 카메라 화면 안에 얼굴이 잘 보이도록 앉아 주세요.")
    if summary.get("front_ratio") is None:
        return tips

    if summary["front_ratio"] >= 0.8:
        tips.append(f"답변 시간의 {summary['front_ratio']:.0%} 동안 정면을 향했습니다. 면접관을 바라보는 태도가 좋아요.")
    else:
        tips.append(f"정면을 향한 비율이 {summary['front_ratio']:.0%}입니다. 생각할 때도 고개를 크게 돌리지 말고 카메라(면접관) 쪽을 바라보세요.")
    if summary["down_ratio"] >= 0.2:
        tips.append(f"고개를 숙인 시간이 {summary['down_ratio']:.0%}입니다. 자신감 있게 고개를 들어 보세요.")
    if summary["side_ratio"] >= 0.2:
        tips.append(f"고개가 옆으로 돌아간 시간이 {summary['side_ratio']:.0%}입니다.")
    if summary["tilt_ratio"] >= 0.3:
        tips.append(f"고개가 한쪽으로 기울어진 시간이 {summary['tilt_ratio']:.0%}입니다. (평균 {summary['avg_abs_roll']}도) 바른 자세를 유지해 보세요.")
    if summary["centered_ratio"] < 0.6:
        tips.append("얼굴이 화면 중앙에서 벗어난 시간이 많습니다. 카메라 정면에 앉아 주세요.")
    if summary["avg_face_size"] < FACE_SIZE_MIN:
        tips.append("카메라와의 거리가 멉니다. 조금 더 가까이 앉아 주세요.")
    elif summary["avg_face_size"] > FACE_SIZE_MAX:
        tips.append("카메라와 너무 가깝습니다. 조금 뒤로 앉아 주세요.")
    if summary["movement"] > 0.5:
        tips.append("머리 움직임이 많은 편입니다. 몸을 흔들지 않고 안정된 자세를 유지해 보세요.")
    elif summary["movement"] < 0.2:
        tips.append("머리 위치가 안정적으로 유지되었습니다.")
    return tips


# ---------------------------------------------------------------------------
# 카메라를 백그라운드에서 계속 돌리는 관리자
# ---------------------------------------------------------------------------

class CameraManager:
    """카메라를 별도 스레드에서 실행하며 최신 영상과 분석 결과를 보관한다"""

    def __init__(self):
        self.camera = None
        self.analyzer = None
        self.thread = None
        self.running = False
        self.source = None
        self.error = None
        self.lock = threading.Lock()   # 여러 스레드가 동시에 값을 바꾸지 않도록 잠금
        self.latest_jpeg = None
        self.latest_result = None
        self.fps = 0.0
        self.collecting = False
        self.samples = []
        self.all_samples = []

    def start(self, source):
        """카메라를 켜고 분석 스레드를 시작한다"""
        if self.running:
            self.stop()
        self.error = None
        try:
            if self.analyzer is None:
                self.analyzer = FaceAnalyzer()
            self.camera = Camera(source)
        except Exception as error:
            self.error = f"카메라를 시작할 수 없습니다: {error}"
            self.camera = None
            raise RuntimeError(self.error)

        self.source = source
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        """카메라를 끈다.
        카메라를 직접 닫지 않고 running을 False로 바꿔 스레드에게 멈추라고 알린다.
        (윈도우에서는 영상을 읽는 도중 다른 스레드가 카메라를 닫으면 프로그램이 멈출 수 있어서,
         카메라는 _loop 스레드가 스스로 닫는다)"""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=3)  # 최대 3초만 기다린다 (멈춰 있어도 서버 종료를 막지 않도록)
            self.thread = None
        self.camera = None
        self.latest_jpeg = None
        self.latest_result = None

    def _loop(self):
        """카메라가 켜져 있는 동안 반복: 프레임 읽기 → 분석 → 그리기 → 저장"""
        camera = self.camera
        last_time = time.time()
        while self.running:
            try:
                frame = camera.read()
                if frame is None:
                    time.sleep(0.05)
                    continue
                result = self.analyzer.analyze(frame)
                frame = draw_result(frame, result)
                ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            except Exception as error:
                # 카메라 연결이 끊기는 등 오류가 나면 기록하고 잠시 후 다시 시도한다
                self.error = f"영상 처리 오류: {error}"
                time.sleep(0.5)
                continue

            now = time.time()
            with self.lock:
                if ok:
                    self.latest_jpeg = jpeg.tobytes()
                self.latest_result = result
                # 면접 중이면 분석 결과를 모은다 (그리기용 좌표는 빼고 저장)
                if self.collecting:
                    sample = {k: v for k, v in result.items() if k not in ("box", "points")}
                    self.samples.append(sample)
                # 초당 처리 프레임 수(FPS)를 부드럽게 계산
                self.fps = 0.9 * self.fps + 0.1 * (1 / max(now - last_time, 0.001))
            last_time = now

        # 반복이 끝나면(카메라 끄기) 이 스레드가 직접 카메라를 닫는다
        camera.close()

    def start_collecting(self):
        """면접 시작: 분석 결과 모으기를 시작한다"""
        with self.lock:
            self.samples = []        # 지금 질문에 대한 분석 결과
            self.all_samples = []    # 면접 전체 분석 결과
            self.collecting = True

    def take_summary(self):
        """질문 1개 끝: 지금까지 모은 결과를 요약해서 돌려주고, 다음 질문을 위해 새로 모으기 시작한다"""
        with self.lock:
            samples = self.samples
            self.all_samples += samples
            self.samples = []
        return summarize_samples(samples)

    def finish_collecting(self):
        """면접 끝: 모으기를 멈추고 면접 전체 결과를 요약해서 돌려준다"""
        with self.lock:
            all_samples = self.all_samples + self.samples
            self.collecting = False
            self.samples = []
            self.all_samples = []
        return summarize_samples(all_samples)

    def get_status(self):
        with self.lock:
            return {
                "running": self.running,
                "source": self.source,
                "error": self.error,
                "fps": round(self.fps, 1),
                "collecting": self.collecting,
                "result": self.latest_result,
            }


# 프로그램 전체에서 카메라 관리자는 하나만 사용한다
camera_manager = CameraManager()


# ---------------------------------------------------------------------------
# 카메라 단독 테스트 (서버 없이 카메라와 얼굴 분석만 확인할 때)
#   라즈베리파이:  python vision.py picamera
#   USB 웹캠:      python vision.py webcam
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    test_source = sys.argv[1] if len(sys.argv) > 1 else "picamera"
    test_camera = Camera(test_source)
    test_analyzer = FaceAnalyzer()
    print(f"[{test_source}] 카메라 테스트를 시작합니다. 30프레임을 분석합니다.")
    start_time = time.time()
    for i in range(30):
        test_frame = test_camera.read()
        if test_frame is None:
            print("프레임을 읽지 못했습니다.")
            continue
        test_result = test_analyzer.analyze(test_frame)
        if test_result["face_detected"]:
            print(f"{i + 1:2d}: {test_result['direction']:5s} yaw={test_result['yaw']:+6.1f} "
                  f"roll={test_result['roll']:+6.1f} pitch={test_result['pitch_ratio']:.2f}")
        else:
            print(f"{i + 1:2d}: 얼굴 없음")
    print(f"평균 속도: {30 / (time.time() - start_time):.1f} FPS")
    cv2.imwrite("camera_test.jpg", draw_result(test_frame, test_result))
    print("마지막 프레임을 camera_test.jpg로 저장했습니다.")
    test_camera.close()
