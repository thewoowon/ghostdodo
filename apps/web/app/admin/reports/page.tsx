import { cookies } from "next/headers";

import { AdminGate } from "@/components/admin/AdminGate";
import { ReviewQueue } from "@/components/admin/ReviewQueue";
import { fetchQueue } from "@/lib/api/admin";
import { load } from "@/lib/api/load";

import styles from "./page.module.css";

// Moderation state changes constantly; a cached queue would show work another
// moderator has already done.
export const dynamic = "force-dynamic";

export default async function AdminReportsPage() {
  const cookieHeader = (await cookies()).toString();
  const result = await load(() => fetchQueue(cookieHeader));

  if (!result.ok) {
    if (result.failure === "unavailable") {
      return <p className={styles.error}>지금은 콘솔을 불러올 수 없습니다.</p>;
    }
    // Authorization is the API's answer, not a guess made here.
    return (
      <AdminGate
        reason={result.failure === "unauthenticated" ? "unauthenticated" : "forbidden"}
      />
    );
  }

  return (
    <section>
      <h2 className={styles.heading}>
        검토 대기 <span className="gd-tabular">{result.data.length}</span>건
      </h2>
      <ReviewQueue initial={result.data} />
    </section>
  );
}
