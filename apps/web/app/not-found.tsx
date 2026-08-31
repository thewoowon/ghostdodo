import Link from "next/link";

import { DodoMark } from "@/components/brand/svg/DodoMark";

import styles from "./not-found.module.css";

/** Brand-consistent 404. Custom illustration, no emoji (docs/04 §9). */
export default function NotFound() {
  return (
    <div className={`gd-shell ${styles.wrap}`}>
      <DodoMark size={72} variant="outline" className={styles.mark} />
      <h1 className={styles.title}>흔적을 찾지 못했습니다</h1>
      <p className={styles.body}>
        요청하신 페이지가 없거나, 아직 도감에 등록되지 않은 회사입니다.
      </p>
      <Link href="/" className={styles.cta}>
        회사 검색하러 가기
      </Link>
    </div>
  );
}
