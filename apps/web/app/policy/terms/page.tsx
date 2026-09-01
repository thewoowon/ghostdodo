import type { Metadata } from "next";
import Link from "next/link";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "이용약관",
  description: "GhostDodo 서비스 이용 조건과 이용자·운영자의 책임.",
  alternates: { canonical: "/policy/terms" },
};

/**
 * Terms of service. A product document describing how the service actually
 * behaves; Korean counsel must review it before public launch.
 */
export default function TermsPage() {
  return (
    <PolicyPage
      title="이용약관"
      lede="고스트도도는 지원자가 직접 겪은 채용 커뮤니케이션을 구조화된 형태로 기록하는 서비스입니다."
    >
      <section>
        <h2>서비스의 성격</h2>
        <p>
        고스트도도가 공개하는 것은 이용자가 제출한 <strong>관측 기록</strong>과
          그 집계입니다. 특정 기업에 대한 평가나 단정적 판단이 아니며, 모든
          지표에는 표본 수와 집계 기간이 함께 표시됩니다. 표본이 부족한 회사에
          대해서는 비율을 공개하지 않습니다.
        </p>
      </section>

      <section>
        <h2>이용계약의 성립</h2>
        <p>
          별도의 가입 절차는 없습니다. 이메일 링크 또는 구글 계정으로 처음
          로그인하는 시점에 계정이 생성되며, 그때 이 약관에 따른 이용계약이
          성립합니다. 공개된 회사 페이지와 지표는 로그인 없이도 볼 수 있습니다.
        </p>
      </section>

      <section>
        <h2>계정과 해지</h2>
        <p>
          이용자는 언제든지 탈퇴를 요청할 수 있으며, 요청은{" "}
          <strong>privacy@ghostdodo.com</strong>으로 접수합니다. 탈퇴하면 계정
          정보는 파기되고 작성한 기록과 계정의 연결은 해제됩니다.
        </p>
        <p>
          이미 공개 지표에 반영된 기록은 다른 이용자에게 제공된 정보의 정확성과
          관련되므로, 탈퇴만으로 자동 삭제되지는 않습니다. 개별 기록의 삭제
          요청은 같은 창구로 접수해 주세요.
        </p>
      </section>

      <section>
        <h2>이용자의 책임</h2>
        <ul>
          <li>본인이 직접 겪은 사실만 기록합니다.</li>
          <li>
            개인의 실명·연락처를 기록하거나, 개인의 의도·인격을 단정하지
            않습니다.
          </li>
          <li>
            첨부 자료를 올리기 전에 타인의 개인정보를 가립니다.
          </li>
          <li>
            동일한 전형에 대해 중복으로 기록하거나, 조직적으로 기록을 조작하지
            않습니다.
          </li>
        </ul>
        <p>
          자세한 내용은 <Link href="/policy/reporting">기록 정책</Link>을 따릅니다.
        </p>
      </section>

      <section>
        <h2>기록의 처리</h2>
        <p>
          제출된 기록은 검토를 거쳐 공개 지표에 반영됩니다. 정책을 위반하거나
          사실관계가 확인되지 않은 기록은 반려·재분류·삭제될 수 있으며, 반복적인
          위반이나 조직적 활동이 확인되면 계정의 기여 권한이 제한될 수 있습니다.
        </p>
        <p>
          검토 절차는 <Link href="/policy/verification">검증 정책</Link>에
          따릅니다.
        </p>
      </section>

      <section>
        <h2>기업의 권리</h2>
        <p>
          기업은 기록의 사실관계에 대해 정정을 요청할 수 있습니다. 정정 절차는
          기록의 내용을 다루며, 작성자를 특정하지 않습니다. 페이지 소유권을
          확인한 기업이라도 <strong>기록을 삭제할 권한은 없습니다.</strong>
        </p>
      </section>

      <section>
        <h2>금지되는 행위</h2>
        <ul>
          <li>허위 기록 제출</li>
          <li>타인의 개인정보 게시</li>
          <li>자동화된 수단을 이용한 대량 수집 또는 제출</li>
          <li>서비스 운영을 방해하는 행위</li>
        </ul>
      </section>

      <section>
        <h2>면책</h2>
        <p>
        고스트도도는 이용자가 제출한 기록의 매개자로서 검증 절차를 운영하지만,
          모든 기록의 진위를 보증하지 않습니다. 지표는 제출된 표본에 기반한
          추정이며, 해당 기업의 모든 채용 과정을 대표하지 않습니다. 이용자는
          지표를 참고 정보로 활용해 주세요.
        </p>
      </section>

      <section>
        <h2>권리침해 신고</h2>
        <p>
          공개된 기록이 자신의 권리를 침해한다고 판단하는 경우, 침해 사실을
          소명하여 삭제 또는 반박 게재를 요청할 수 있습니다. 요청은{" "}
          <strong>privacy@ghostdodo.com</strong>으로 접수합니다.
        </p>
        <p>
          접수된 요청은 관계 법령에 따라 검토하며, 권리 침해 여부를 판단하기
          어려운 경우 해당 기록의 게시를 일정 기간 중단할 수 있습니다. 이
          절차는 사실관계를 다투기 위한{" "}
          <Link href="/policy/reporting">기록 정책</Link>상의 정정 요청과는
          별개입니다.
        </p>
      </section>

      <section>
        <h2>서비스의 변경과 중단</h2>
        <p>
          서비스의 내용은 변경될 수 있으며, 운영상·기술상 필요가 있는 경우
          서비스의 전부 또는 일부를 중단할 수 있습니다. 예정된 중단은 미리
          공지하고, 예상하지 못한 사유로 중단되는 경우에는 사후에 알립니다.
        </p>
      </section>

      <section>
        <h2>약관의 변경</h2>
        <p>
          약관이 변경되는 경우 변경 내용과 시행일을 시행 7일 전까지 서비스 내에
          공지합니다. 이용자에게 불리한 변경은 시행 30일 전까지 공지합니다.
          공지된 시행일까지 이의를 제기하지 않으면 변경에 동의한 것으로 보며,
          동의하지 않는 경우 탈퇴할 수 있습니다.
        </p>
        <p>
          지표 산출 기준이 변경되는 경우에는{" "}
          <Link href="/methodology">측정 기준</Link> 페이지의 버전이 함께
          갱신됩니다.
        </p>
      </section>

      <section>
        <h2>준거법과 관할</h2>
        <p>
          이 약관과 서비스 이용에는 대한민국 법을 적용합니다. 서비스 이용과
          관련하여 분쟁이 발생한 경우 민사소송법이 정한 법원을 관할 법원으로
          합니다.
        </p>
      </section>

      <section>
        <h2>운영자 정보와 문의</h2>
        <p>
          고스트도도는 개인이 운영하는 서비스입니다. 서비스 이용과 약관에 관한
          문의는 <strong>privacy@ghostdodo.com</strong>으로 접수합니다.
        </p>
        <p>시행일 — 서비스 공개일</p>
      </section>
    </PolicyPage>
  );
}
