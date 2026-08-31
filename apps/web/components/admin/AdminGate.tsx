import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";

import styles from "./AdminGate.module.css";

/**
 * Shown when the server refused an admin request.
 *
 * The console is authorized by the API on every call, so this is a
 * presentation of the server's answer rather than a client-side permission
 * check. It deliberately does not reveal whether the queue has anything in
 * it.
 */
export function AdminGate({ reason }: { reason: "unauthenticated" | "forbidden" }) {
  return (
    <div className={styles.wrap}>
      <DodoMark size={56} variant="outline" className={styles.mark} />
      <h2 className={styles.title}>
        {reason === "unauthenticated"
          ? "로그인이 필요합니다"
          : "접근 권한이 없습니다"}
      </h2>
      <p className={styles.body}>
        {reason === "unauthenticated"
          ? "운영 콘솔은 로그인 후 이용할 수 있습니다."
          : "이 콘솔은 검토 권한이 있는 계정만 사용할 수 있습니다."}
      </p>
      <Link href="/" className={styles.link}>
        홈으로
      </Link>
    </div>
  );
}
