import type { Metadata } from "next";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "기록 정책",
  description: "GhostDodo에 무엇을 기록할 수 있고, 무엇을 기록할 수 없는지.",
  alternates: { canonical: "/policy/reporting" },
};

export default function ReportingPolicyPage() {
  return (
    <PolicyPage
      title="기록 정책"
      lede="고스트도도는 감정이 아니라 사건을 기록합니다. 아래 원칙은 서비스 설계와 검토 기준 모두에 동일하게 적용됩니다."
    >
      <section>
        <h2>기록할 수 있는 것</h2>
        <ul>
          <li>지원 시점, 진행한 전형 단계, 마지막으로 회사와 연락한 시점</li>
          <li>회사가 밝힌 결과 안내 예정일과 실제 통보 여부</li>
          <li>합격·불합격 등 통보받은 결과와 전달 경로</li>
          <li>본인이 직접 겪은 과정에 한정된 사실</li>
        </ul>
      </section>

      <section>
        <h2>기록할 수 없는 것</h2>
        <ul>
          <li>면접관·인사담당자 등 개인의 실명이나 연락처</li>
          <li>제3자의 개인정보가 포함된 자료</li>
          <li>범죄·부정 행위를 단정하는 주장</li>
          <li>개인의 의도나 인격에 대한 추측</li>
          <li>직접 겪지 않은 전언</li>
        </ul>
        <p>
          자유 서술은 짧은 맥락 보충용이며 길이에 제한이 있습니다. 판단은 구조화된
          항목으로 남기고, 서술은 사실을 보충하는 데에만 사용해 주세요.
        </p>
      </section>

      <section>
        <h2>첨부 자료</h2>
        <p>
          결과 메일 스크린샷 같은 자료는 <strong>검증 목적으로만</strong>{" "}
          사용되며 공개되지 않습니다. 업로드 전에 타인의 이름, 전화번호, 이메일
          주소, 식별번호를 가려 주세요.
        </p>
      </section>

      <section>
        <h2>기여에 대한 보상</h2>
        <p>
          평판 점수는 기록의 <strong>완결성과 검증 가능성</strong>에 따라
          올라갑니다. 부정적인 기록을 더 많이 남긴다고 해서 더 많은 점수를 받지
          않습니다. 응답이 빨랐다는 기록과 응답이 없었다는 기록의 보상은
          동일합니다.
        </p>
      </section>
    </PolicyPage>
  );
}
