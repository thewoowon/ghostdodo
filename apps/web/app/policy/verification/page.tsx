import type { Metadata } from "next";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "검증 정책",
  description: "기록이 어떤 절차로 검증되고, 어떤 경우 공개 지표에 반영되는지.",
  alternates: { canonical: "/policy/verification" },
};

export default function VerificationPolicyPage() {
  return (
    <PolicyPage
      title="검증 정책"
      lede="모든 기록이 곧바로 공개 지표가 되지는 않습니다. 아래 절차를 거친 기록만 회사 페이지의 숫자에 반영됩니다."
    >
      <section>
        <h2>검증 단계</h2>
        <ol>
          <li>
            <strong>자동 검사</strong> — 불가능한 날짜, 중복 제출, 개인정보로
            의심되는 문자열을 기계적으로 확인합니다.
          </li>
          <li>
            <strong>검토 대기</strong> — 자동 검사에서 표시된 기록은 사람이 먼저
            확인합니다.
          </li>
          <li>
            <strong>검증</strong> — 첨부 자료와 기록의 일관성을 확인합니다.
          </li>
          <li>
            <strong>집계</strong> — 검증된 기록만 회사 지표를 다시 계산합니다.
          </li>
        </ol>
      </section>

      <section>
        <h2>상태</h2>
        <ul>
          <li><strong>검증됨</strong> — 자료 또는 정황이 검증 기준을 충족</li>
          <li><strong>부분 검증</strong> — 일부 항목만 확인됨</li>
          <li><strong>이의 제기됨</strong> — 사실관계 정정 요청이 진행 중</li>
          <li><strong>반려됨</strong> — 기준을 충족하지 못해 집계에서 제외</li>
        </ul>
      </section>

      <section>
        <h2>정정과 이의 제기</h2>
        <p>
          회사 관계자는 기록에 대한 정정을 요청할 수 있습니다. 이 절차는{" "}
          <strong>기록의 내용</strong>을 다루며, 작성자를 특정하거나 신원을
          회사에 알리지 않습니다. 정정으로 기록이 수정·재분류·삭제되면 해당
          회사의 지표는 다시 계산됩니다.
        </p>
        <p>
          페이지 소유권을 확인한 기업이라도 기록을 삭제할 권한은 없습니다.
        </p>
      </section>

      <section>
        <h2>비정상 패턴</h2>
        <p>
          단기간에 몰린 기록, 동일한 문장, 동일한 첨부 파일, 새로 만든 계정
          집단 등 조직적 활동으로 의심되는 경우 해당 기록은 검토가 끝날 때까지
          공개 집계에서 일시적으로 제외됩니다.
        </p>
      </section>
    </PolicyPage>
  );
}
