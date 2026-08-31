import { cookies } from "next/headers";

import { AdminGate } from "@/components/admin/AdminGate";
import { ReviewQueue } from "@/components/admin/ReviewQueue";
import { fetchQueue } from "@/lib/api/admin";
import { ApiError, ApiUnavailableError } from "@/lib/api/client";

import styles from "./page.module.css";

// Moderation state changes constantly; a cached queue would show work that
// another moderator has already done.
export const dynamic = "force-dynamic";

export default async function AdminReportsPage() {
  const cookieHeader = (await cookies()).toString();

  try {
    const items = await fetchQueue(cookieHeader);
    return (
      <section>
        <h2 className={styles.heading}>
          검토 대기 <span className="gd-tabular">{items.length}</span>건
        </h2>
        <ReviewQueue initial={items} />
      </section>
    );
  } catch (error) {
    // Authorization is the API's answer, not a guess made here.
    if (error instanceof ApiError && error.status === 401) {
      return <AdminGate reason="unauthenticated" />;
    }
    if (error instanceof ApiError && error.status === 403) {
      return <AdminGate reason="forbidden" />;
    }
    if (error instanceof ApiUnavailableError) {
      return <p className={styles.error}>지금은 콘솔을 불러올 수 없습니다.</p>;
    }
    throw error;
  }
}
