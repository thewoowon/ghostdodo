import { cookies } from "next/headers";

import { AdminGate } from "@/components/admin/AdminGate";
import { CompanyRequestQueue } from "@/components/admin/CompanyRequestQueue";
import { fetchCompanyRequests } from "@/lib/api/admin";
import { load } from "@/lib/api/load";

import styles from "../reports/page.module.css";

export const dynamic = "force-dynamic";

export default async function AdminCompanyRequestsPage() {
  const cookieHeader = (await cookies()).toString();
  const result = await load(() => fetchCompanyRequests(cookieHeader));

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
        회사 등록 요청 <span className="gd-tabular">{result.data.length}</span>건
      </h2>
      <CompanyRequestQueue initial={result.data} />
    </section>
  );
}
