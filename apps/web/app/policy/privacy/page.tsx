import type { Metadata } from "next";
import Link from "next/link";

import { PolicyPage } from "@/components/ui/PolicyPage";

export const metadata: Metadata = {
  title: "개인정보처리방침",
  description:
    "GhostDodo가 수집하는 개인정보의 항목과 목적, 보관 기간, 이용자의 권리를 설명합니다.",
  alternates: { canonical: "/policy/privacy" },
};

/**
 * Privacy policy.
 *
 * Written against what the code actually does — the fields the schema stores,
 * the hashing in core/security.py, and the retention behaviour of the audit
 * tables. It is a description of the system, not boilerplate, so it stays
 * true only as long as someone updates it alongside the schema.
 *
 * Section order follows 개인정보 보호법 제30조 so a reviewer can walk it
 * against the statute without reordering anything.
 *
 * This is a product document, not legal advice. Korean counsel must review
 * it before public launch (docs/08 §11); the open questions and the data
 * inventory are in docs/legal/REVIEW_REQUEST.md.
 */
export default function PrivacyPolicyPage() {
  return (
    <PolicyPage
      title="개인정보처리방침"
      lede="고스트도도는 채용 커뮤니케이션 기록을 다루는 서비스로서, 목적에 필요한 최소한의 정보만 수집합니다."
    >
      <section>
        <h2>수집하는 항목</h2>
        <ul>
          <li>
            <strong>계정</strong> — 이메일 주소, 서비스 내 표시용 필명. 필명은
            자동 생성되며 이메일에서 유추할 수 없습니다.
          </li>
          <li>
            <strong>구글 로그인을 사용하는 경우</strong> — 구글이 제공하는 계정
            식별자와 인증된 이메일 주소. 비밀번호는 전달받지 않습니다.
          </li>
          <li>
            <strong>기록</strong> — 회사, 직무, 전형 단계, 지원일, 연락 시점,
            결과 통보 여부와 시점, 짧은 맥락 설명.
          </li>
          <li>
            <strong>첨부 자료</strong> — 이용자가 직접 업로드한 결과 메일
            스크린샷 등. 검증 목적에만 사용됩니다.
          </li>
          <li>
            <strong>접속 정보</strong> — 남용 방지를 위한 IP 주소의{" "}
            <strong>해시값</strong>. 원본 IP는 저장하지 않습니다.
          </li>
        </ul>
      </section>

      <section>
        <h2>수집하지 않는 항목</h2>
        <p>
          주민등록번호, 상세 주소, 채용 담당자의 개인 연락처, 사상·건강·성적
          지향 등 민감정보는 수집하지 않으며, 수집을 요구하지도 않습니다.
          비밀번호를 사용하지 않으므로 비밀번호도 보관하지 않습니다.
        </p>
      </section>

      <section>
        <h2>이용 목적</h2>
        <ul>
          <li>회사별 채용 응답 지표 산출 (개인 식별 정보 없이 집계)</li>
          <li>기록의 검증 및 중복·조작 방지</li>
          <li>로그인 및 계정 유지</li>
          <li>법령 준수 및 분쟁 대응</li>
        </ul>
        <p>
          수집한 개인정보는 위 목적 외의 용도로 이용하지 않으며, 목적이
          변경되는 경우 사전에 알리고 필요한 동의를 받습니다.
        </p>
      </section>

      <section>
        <h2>공개되는 정보와 공개되지 않는 정보</h2>
        <p>
          회사 페이지에 공개되는 것은 <strong>구조화된 사건</strong>입니다. 전형
          단계, 날짜, 결과 통보 여부, 검증 상태가 이에 해당합니다.
        </p>
        <p>
          <strong>작성자를 식별할 수 있는 정보는 공개되지 않습니다.</strong>{" "}
          이메일, 필명, 계정 식별자는 회사 페이지 어디에도 표시되지 않으며,
          기업이 정정을 요청하는 절차에서도 회사에 제공되지 않습니다. 첨부 자료
          역시 공개되지 않고, 검토 권한이 있는 운영자만 시간 제한이 있는 링크로
          열람하며 모든 열람은 기록됩니다.
        </p>
      </section>

      <section>
        <h2>보유 및 이용 기간</h2>
        <ul>
          <li>
            <strong>계정 정보</strong> — 탈퇴 요청을 접수한 때까지. 접수 후 지체
            없이 파기합니다.
          </li>
          <li>
            <strong>기록</strong> — 서비스 운영 기간 동안 보유하며, 삭제 요청은
            아래 &lsquo;이용자의 권리와 행사 방법&rsquo;에 따릅니다.
          </li>
          <li>
            <strong>첨부 자료</strong> — 검증 완료 후 이용자가 삭제할 수 있으며,
            분쟁이 진행 중인 경우 절차 종료까지 보관될 수 있습니다.
          </li>
          <li>
            <strong>로그인 링크</strong> — 발급 후 15분. 한 번 사용되면 즉시
            무효화됩니다.
          </li>
          <li>
            <strong>운영 감사 기록</strong> — 모더레이션 결정과 첨부 자료 열람
            이력을 추적하기 위해 별도 보관합니다. 이 기록에는 처리를 수행한
            운영자와 대상 기록의 식별자가 포함되며, 계정이 삭제되면 해당 연결은
            해제됩니다.
          </li>
        </ul>
      </section>

      <section>
        <h2>파기 절차 및 방법</h2>
        <p>
          보유 기간이 지나거나 처리 목적이 달성된 개인정보는 지체 없이
          파기합니다. 데이터베이스에 저장된 정보는 복구할 수 없는 방법으로
          삭제하고, 첨부 자료는 저장소에서 객체 자체를 삭제합니다.
        </p>
        <p>
          다른 법령에 따라 보존해야 하는 정보는 해당 기간 동안 다른 개인정보와
          분리하여 보관한 뒤 파기합니다.
        </p>
      </section>

      <section>
        <h2>처리위탁 및 국외 이전</h2>
        <p>
          서비스 운영에 필요한 범위에서 아래와 같이 처리를 위탁하고 있으며, 일부
          업무는 국외에서 처리됩니다.
        </p>
        <ul>
          <li>
            <strong>Railway Corp. (미국)</strong> — 서버와 데이터베이스 운영.
            계정 정보와 기록 전체가 서비스 이용 시 네트워크를 통해 이전되며,
            위탁 계약이 끝날 때까지 보유합니다.
          </li>
          <li>
            <strong>Amazon Web Services (대한민국, 서울 리전)</strong> — 첨부
            자료 저장. 업로드 시점에 이전되며 삭제 시까지 보유합니다.
          </li>
          <li>
            <strong>Resend, Inc. (미국)</strong> — 로그인 링크 이메일 발송.
            이메일 주소가 발송 요청 시점에 이전되며, 발송 후 지체 없이
            파기됩니다.
          </li>
          <li>
            <strong>Vercel Inc. (미국 등)</strong> — 웹 페이지 제공. 요청이
            경유할 뿐 개인정보를 별도로 저장하지 않습니다.
          </li>
        </ul>
        <p>
          국외 이전을 거부하려면 서비스를 이용하지 않는 방법 외에는 없으며, 이
          경우 계정 생성과 기록 작성을 할 수 없습니다.
        </p>
      </section>

      <section>
        <h2>제3자 제공</h2>
        <p>
          개인정보를 제3자에게 판매하거나 제공하지 않습니다. 기업이 후원하거나
          페이지 소유권을 확인하더라도 작성자 정보에 접근할 수 없으며, 지표
          계산에도 영향을 주지 않습니다. 법령에 따른 요청이 있는 경우에만 관계
          법령이 정한 절차와 범위에서 제공합니다.
        </p>
      </section>

      <section>
        <h2>쿠키 등 자동 수집 장치</h2>
        <p>
          로그인 상태를 유지하기 위한 세션 쿠키 한 종류만 사용합니다. 이 쿠키는
          스크립트로 읽을 수 없도록 설정되어 있으며, 광고나 행태정보 분석을 위한
          쿠키는 사용하지 않습니다.
        </p>
        <p>
          브라우저 설정에서 쿠키 저장을 거부할 수 있습니다. 다만 거부하는 경우
          로그인이 필요한 기능은 이용할 수 없습니다.
        </p>
      </section>

      <section>
        <h2>이용자의 권리와 행사 방법</h2>
        <p>
          본인의 개인정보에 대해 열람, 정정, 삭제, 처리 정지를 요청할 수 있으며,
          언제든지 탈퇴를 요청할 수 있습니다. 요청은{" "}
          <strong>privacy@ghostdodo.com</strong>으로 접수하며, 접수일로부터 10일
          이내에 처리하고 결과를 알려 드립니다.
        </p>
        <p>
          이미 공개 지표에 반영된 기록의 삭제는 다른 이용자에게 제공된 정보의
          정확성과 관련되므로, 삭제 대신 정정 또는 재분류로 처리될 수 있습니다.
          계정을 삭제하면 작성한 기록과 계정의 연결은 해제됩니다.
        </p>
        <p>
          기록의 사실관계에 대한 정정은{" "}
          <Link href="/company-portal/claim">정정 요청 절차</Link>를 이용해
          주세요.
        </p>
      </section>

      <section>
        <h2>안전성 확보 조치</h2>
        <ul>
          <li>
            비밀번호를 사용하지 않는 로그인 방식이므로 비밀번호를 보관하지
            않습니다.
          </li>
          <li>
            IP 주소는 원본을 저장하지 않고 복원할 수 없는 해시값으로만 다룹니다.
          </li>
          <li>
            첨부 자료는 비공개 저장소에 두고, 시간 제한이 있는 링크로만 열람할
            수 있습니다.
          </li>
          <li>
            운영자의 첨부 자료 열람은 예외 없이 기록되며, 이 기록은 수정하거나
            삭제할 수 없습니다.
          </li>
          <li>권한은 역할에 따라 분리되어 있고, 통신 구간은 암호화됩니다.</li>
        </ul>
      </section>

      <section>
        <h2>개인정보 보호책임자</h2>
        <p>
          개인정보 처리에 관한 업무를 총괄하고 이용자의 문의와 권리행사 요청을
          처리하기 위해 아래와 같이 개인정보 보호책임자를 두고 있습니다.
        </p>
        <ul>
          <li>
            <strong>개인정보 보호책임자</strong> — 고스트도도 운영자
          </li>
          <li>
            <strong>연락처</strong> — privacy@ghostdodo.com
          </li>
        </ul>
      </section>

      <section>
        <h2>권익침해 구제 방법</h2>
        <p>
          개인정보 침해에 관한 상담이나 분쟁 해결이 필요한 경우 아래 기관에
          도움을 요청할 수 있습니다.
        </p>
        <ul>
          <li>개인정보분쟁조정위원회 — 1833-6972 (www.kopico.go.kr)</li>
          <li>개인정보침해신고센터 — 118 (privacy.kisa.or.kr)</li>
          <li>대검찰청 사이버수사과 — 1301 (www.spo.go.kr)</li>
          <li>경찰청 사이버수사국 — 182 (ecrm.police.go.kr)</li>
        </ul>
        <p>
          개인정보 보호법 제35조, 제36조, 제37조에 따른 요구에 대한 처리 결과에
          이의가 있는 경우 행정심판을 청구할 수 있습니다.
        </p>
      </section>

      <section>
        <h2>방침의 시행과 변경</h2>
        <p>
          이 방침이 변경되는 경우 변경 내용과 시행일을 서비스 내에 미리
          공지합니다. 이용자에게 불리한 변경은 시행일로부터 30일 전에
          공지합니다.
        </p>
        <p>시행일 — 서비스 공개일</p>
      </section>
    </PolicyPage>
  );
}
