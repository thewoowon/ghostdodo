import type { Metadata } from "next";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "소개",
  description: "GhostDodo가 무엇을 하고, 무엇을 하지 않는 서비스인지.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <PolicyPage
      title="GhostDodo 소개"
      lede="지원해본 사람만 알 수 있는 채용 커뮤니케이션 기록을 구조화된 데이터로 남깁니다."
    >
      <section>
        <h2>왜 만들었나</h2>
        <p>
          지원서, 코딩 테스트, 과제, 면접에 며칠에서 몇 주를 쓰고도 아무런 결과
          통보를 받지 못하는 일이 반복됩니다. 개별 경험담은 커뮤니티에 흩어져
          있지만, 어떤 회사가 결과를 알려주는지는 지원하기 전에 확인할 방법이
          없었습니다. GhostDodo는 그 정보를 구조화된 공개 데이터로 만듭니다.
        </p>
      </section>

      <section>
        <h2>무엇을 하지 않나</h2>
        <ul>
          <li>블랙리스트를 만들지 않습니다.</li>
          <li>기업을 단정적으로 비방하지 않습니다.</li>
          <li>표본이 부족한 회사에 순위를 매기지 않습니다.</li>
          <li>추측한 숫자를 지표로 표시하지 않습니다.</li>
          <li>작성자의 신원을 회사에 알리지 않습니다.</li>
        </ul>
      </section>

      <section>
        <h2>다른 서비스와의 차이</h2>
        <p>
          재직자의 내부 이야기나 근무 환경 평가와는 다릅니다. GhostDodo가 다루는
          것은 <strong>지원자가 겪은 채용 과정의 커뮤니케이션</strong> 하나이며,
          그 범위를 넘지 않습니다.
        </p>
      </section>

      <section>
        <h2>응답이 빠른 회사도 똑같이 보여줍니다</h2>
        <p>
          결과를 성실히 통보하는 회사는 그 사실이 드러나야 합니다. 응답률이 높은
          회사와 낮은 회사는 같은 비중으로 표시되며, 지표 계산은 후원이나 광고와
          무관합니다.
        </p>
      </section>
    </PolicyPage>
  );
}
