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
 * This is a product document, not legal advice. Korean counsel must review
 * it before public launch (docs/08 preamble).
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
          역시 공개되지 않고, 검토 권한이 있는 운영자만 시간 제한이 있는
          링크로 열람하며 모든 열람은 기록됩니다.
        </p>
      </section>

      <section>
        <h2>보관 기간</h2>
        <ul>
          <li>계정 정보 — 탈퇴 요청 시까지</li>
          <li>기록 — 서비스 운영 기간 동안 (삭제 요청 시 아래 절차에 따름)</li>
          <li>
            첨부 자료 — 검증 완료 후 이용자가 삭제할 수 있으며, 분쟁이 진행
            중인 경우 절차 종료까지 보관될 수 있습니다.
          </li>
          <li>
            운영 감사 기록 — 모더레이션 결정의 추적을 위해 별도 보관합니다.
            이용자 식별 정보는 포함하지 않습니다.
          </li>
        </ul>
      </section>

      <section>
        <h2>이용자의 권리</h2>
        <p>
          본인의 기록에 대한 열람, 정정, 삭제, 처리 정지를 요청할 수 있습니다.
          다만 이미 공개 지표에 반영된 기록의 삭제는 다른 이용자에게 제공된
          정보의 정확성과 관련되므로, 삭제 대신 정정 또는 재분류로 처리될 수
          있습니다. 계정 삭제 시 작성한 기록과의 연결은 해제됩니다.
        </p>
      </section>

      <section>
        <h2>제3자 제공</h2>
        <p>
          개인정보를 제3자에게 판매하거나 제공하지 않습니다. 기업이 후원하거나
          페이지 소유권을 확인하더라도 작성자 정보에 접근할 수 없으며, 지표
          계산에도 영향을 주지 않습니다.
        </p>
      </section>

      <section>
        <h2>문의</h2>
        <p>
          개인정보 관련 문의와 권리 행사 요청은 서비스 문의 창구를 통해 접수할
          수 있습니다. 기록의 사실관계에 대한 정정은{" "}
          <Link href="/company-portal/claim">정정 요청 절차</Link>를 이용해
          주세요.
        </p>
      </section>
    </PolicyPage>
  );
}
