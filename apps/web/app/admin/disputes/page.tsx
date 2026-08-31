import { cookies } from "next/headers";

import { AdminGate } from "@/components/admin/AdminGate";
import { DisputeQueue } from "@/components/admin/DisputeQueue";
import { fetchDisputes } from "@/lib/api/admin";
import { load } from "@/lib/api/load";

import styles from "../reports/page.module.css";

export const dynamic = "force-dynamic";

export default async function AdminDisputesPage() {
  const cookieHeader = (await cookies()).toString();
  const result = await load(() => fetchDisputes(cookieHeader));

  if (!result.ok) {
    if (result.failure === "unavailable") {
      return <p className={styles.error}>지금은 콘솔을 불러올 수 없습니다.</p>;
    }
    return (
      <AdminGate
        reason={result.failure === "unauthenticated" ? "unauthenticated" : "forbidden"}
      />
    );
  }

  return (
    <section>
      <h2 className={styles.heading}>
        정정 요청 <span className="gd-tabular">{result.data.length}</span>건
      </h2>
      <DisputeQueue initial={result.data} />
    </section>
  );
}
