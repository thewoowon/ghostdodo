import { cookies } from "next/headers";

import { AdminGate } from "@/components/admin/AdminGate";
import { DisputeQueue } from "@/components/admin/DisputeQueue";
import { fetchDisputes } from "@/lib/api/admin";
import { ApiError, ApiUnavailableError } from "@/lib/api/client";

import styles from "../reports/page.module.css";

export const dynamic = "force-dynamic";

export default async function AdminDisputesPage() {
  const cookieHeader = (await cookies()).toString();

  try {
    const items = await fetchDisputes(cookieHeader);
    return (
      <section>
        <h2 className={styles.heading}>
          정정 요청 <span className="gd-tabular">{items.length}</span>건
        </h2>
        <DisputeQueue initial={items} />
      </section>
    );
  } catch (error) {
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
