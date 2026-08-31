import type { Metadata } from "next";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "회사 페이지 정정 요청",
  description: "회사 관계자를 위한 사실관계 정정 및 페이지 소유권 확인 절차.",
  alternates: { canonical: "/company-portal/claim" },
};

export default function CompanyClaimPage() {
  return (
    <PolicyPage
      title="사실관계 정정 요청"
      lede="기록된 내용이 사실과 다르다면 정정을 요청할 수 있습니다. 이 절차는 기록의 내용을 다루며, 작성자를 특정하지 않습니다."
    >
      <section>
        <h2>절차</h2>
        <ol>
          <li>회사 도메인 이메일로 담당자 확인을 요청합니다.</li>
          <li>정정을 요청하는 항목과 사유를 제출합니다.</li>
          <li>운영진이 원본 기록과 첨부 자료를 대조합니다.</li>
          <li>기록이 수정·재분류·삭제되면 지표가 다시 계산됩니다.</li>
          <li>회사의 공식 입장을 회사 페이지에 게시할 수 있습니다.</li>
        </ol>
      </section>

      <section>
        <h2>확인해 주세요</h2>
        <ul>
          <li>
            페이지 소유권을 확인해도 기록을 삭제할 권한은 생기지 않습니다.
          </li>
          <li>
            작성자의 신원은 정정 절차 어느 단계에서도 회사에 제공되지 않습니다.
          </li>
          <li>
            후원이나 광고 집행은 지표 계산에 영향을 주지 않습니다.
          </li>
        </ul>
      </section>

      <section>
        <h2>준비 중</h2>
        <p>
          담당자 확인 및 정정 요청 폼은 준비 중입니다. 그 전까지는 운영팀으로
          직접 문의해 주세요.
        </p>
      </section>
    </PolicyPage>
  );
}
