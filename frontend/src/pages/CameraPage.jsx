// CameraPage.jsx
// 카메라 영상 분석을 따로 확인하고 테스트하는 페이지

import { Link } from 'react-router'
import CameraPanel from '../components/CameraPanel'
import './CameraPage.css'

function CameraPage() {
  return (
    <div>
      <div className="page-header">
        <h1>영상 분석</h1>
        <p>라즈베리파이 카메라 영상에서 얼굴을 찾고, 고개 방향과 자세를 실시간으로 분석합니다.</p>
      </div>

      <div className="camera-page">
        <CameraPanel />

        <div className="camera-guide card">
          <h2>어떻게 분석하나요?</h2>
          <ol>
            <li>
              <strong>영상 입력</strong>
              <p>Raspberry Pi Camera(또는 USB 웹캠)에서 640×480 영상을 계속 읽습니다.</p>
            </li>
            <li>
              <strong>얼굴 검출 (YuNet 모델)</strong>
              <p>OpenCV의 딥러닝 얼굴 검출 모델이 얼굴 위치와 5개 특징점(두 눈, 코끝, 입 양 끝)을 찾습니다.</p>
            </li>
            <li>
              <strong>고개 방향 계산</strong>
              <p>
                두 눈을 이은 선의 각도로 <b>기울기</b>를, 코끝이 두 눈 가운데에서 벗어난 정도로
                <b> 좌우 회전</b>을, 눈과 입 사이에서 코끝의 높이로 <b>상하 방향</b>을 계산합니다.
              </p>
            </li>
            <li>
              <strong>면접 피드백에 활용</strong>
              <p>면접 중 프레임별 결과를 모아 정면 응시 비율, 고개 기울어짐, 움직임을 질문마다 요약합니다.</p>
            </li>
          </ol>

          <p className="notice">
            ※ 얼굴 특징점으로 계산한 고개 방향이며, 눈동자를 추적하는 시선 추적은 아닙니다.
            각도는 대략적인 추정값입니다.
          </p>

          <Link to="/interview/setup" className="button">
            이 상태로 모의면접 시작하기
          </Link>
        </div>
      </div>
    </div>
  )
}

export default CameraPage
