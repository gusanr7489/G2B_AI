import { Table, Tag, Typography, Alert, Collapse } from "antd";
import type { Analysis } from "../api/analyses";

const { Text, Paragraph } = Typography;

const SEVERITY_CONFIG: Record<string, { color: string; label: string }> = {
  safe: { color: "green", label: "정상" },
  caution: { color: "gold", label: "주의" },
  warning: { color: "orange", label: "경고" },
  danger: { color: "red", label: "위험" },
};

const GROUP_LABELS: Record<string, { label: string; color: string }> = {
  S: { label: "과업/산출물", color: "purple" },
  P: { label: "인력/환경", color: "volcano" },
  C: { label: "비용/대가", color: "magenta" },
  L: { label: "법무/지재권", color: "geekblue" },
  O: { label: "기타(미등록)", color: "default" },
};

const POISON_CATEGORIES: Array<{
  code: string;
  name: string;
  criteria: string;
  level: "caution" | "warning" | "danger";
}> = [
  { code: "S1", name: "백지수표형 과업 요구", criteria: "\"필요시 추가 과업 무상 수행\" 명시 — 무한 과업 확장 리스크 사업자 전가", level: "danger" },
  { code: "S2", name: "구축(SI) 수준 산출물 요구", criteria: "ISP/ISMP에 물리 ERD·화면설계서·소스코드 진단 요구 — 컨설팅 대가에 미포함 공수 강제", level: "warning" },
  { code: "S3", name: "과도한 인쇄/번역 비용 전가", criteria: "100부 이상 컬러 인쇄 또는 전문 영문 번역본 의무", level: "caution" },
  { code: "S4", name: "종료 후 무상 자문 강제", criteria: "사업 종료 후 6개월 이상 정기 방문 자문 무상 지원 — 하자보수 범위 초과", level: "warning" },
  { code: "P1", name: "인력 교체 시 인건비 전가", criteria: "7일 이상 중복 투입 인건비를 사업자가 부담 — 1MM에 2인분 인건비 이중 부담", level: "danger" },
  { code: "P2", name: "체재비 없는 지방 상주", criteria: "비수도권 전원 상주 + 체재비/숙소 미지원 — 수도권 인력 수급 불가, 마진 증발", level: "danger" },
  { code: "P3", name: "발주처 일방적 인력 퇴출권", criteria: "협의·소명 절차 없이 3일 이내 즉시 교체 요구 — 노동법 위반 소지", level: "warning" },
  { code: "P4", name: "과도한 PM 직급 제한", criteria: "PM을 등기이사/임원급으로 한정 — 입찰 가능 풀 부당 제한", level: "caution" },
  { code: "C1", name: "인질형 대금 지급", criteria: "잔금을 후속 SI 예산 확보·예타 통과에 연동 — 사업자 통제 불가 요인에 지급 연동", level: "danger" },
  { code: "C2", name: "상용 SW/장비 기증 강요", criteria: "사업자가 EA툴/노트북 구매 후 발주처에 기증 — 자산취득비 용역비 전가", level: "warning" },
  { code: "C3", name: "선금 지급 차단", criteria: "선금 전면 불가 또는 기재부 특례(70~80%) 무시 30% 미만 제한", level: "caution" },
  { code: "C4", name: "출장비 실비 정산 불가", criteria: "전국 단위 현장실사 필수임에도 출장비 제안가 포함 — 예측 불가 비용 사업자 부담", level: "warning" },
  { code: "L1", name: "지식재산권 독점 귀속", criteria: "산출물·방법론·도구 일체 발주기관 단독 귀속 — 계약예규 공동소유 원칙 위반", level: "danger" },
  { code: "L2", name: "물리적 하드디스크 압수", criteria: "사업 종료 시 PC/노트북 HDD 물리 파기·반납 강제 — 완전삭제(Wiping)로 충분", level: "danger" },
  { code: "L3", name: "제3자 저작권 무과실 책임", criteria: "발주처 제공 자료로 인한 분쟁도 사업자 100% 책임 — 발주처 귀책 사유까지 전가", level: "warning" },
  { code: "L4", name: "징벌적 지연배상금", criteria: "1일 0.25% 이상 (법정 0.125% 초과) 또는 상한선(30%) 미설정", level: "caution" },
];

interface Props {
  analysis: Analysis;
}

interface PoisonItem {
  category: string;
  clause: string;
  severity: string;
  reason: string;
  source: string;
}

export default function PoisonClauseView({ analysis }: Props) {
  const poison = analysis.poison_clauses;
  if (!poison) return <Text type="secondary">독소조항 분석 결과가 없습니다</Text>;

  const riskConfig = SEVERITY_CONFIG[poison.risk_level] || SEVERITY_CONFIG.safe;

  const itemColumns = [
    {
      title: "코드",
      dataIndex: "category",
      width: 90,
      render: (v: string) => {
        const code = (v || "").toUpperCase();
        const groupKey = code === "OTHER" ? "O" : code.charAt(0);
        const label = code === "OTHER" ? "기타" : code;
        return <Tag color={GROUP_LABELS[groupKey]?.color}>{label}</Tag>;
      },
    },
    {
      title: "심각도",
      dataIndex: "severity",
      width: 75,
      render: (v: string) => {
        const cfg = SEVERITY_CONFIG[v] || SEVERITY_CONFIG.safe;
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
    {
      title: "조항 내용",
      dataIndex: "clause",
      render: (v: string) => (
        <Paragraph
          style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}
          ellipsis={{ rows: 3, expandable: true, symbol: "전체 보기" }}
        >
          {v || "-"}
        </Paragraph>
      ),
    },
    {
      title: "판단 근거",
      dataIndex: "reason",
      render: (v: string) => (
        <Paragraph
          style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}
          ellipsis={{ rows: 3, expandable: true, symbol: "전체 보기" }}
        >
          {v || "-"}
        </Paragraph>
      ),
    },
    {
      title: "출처",
      dataIndex: "source",
      width: 160,
      render: (v: string) => (
        <Text style={{ fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
          {v || "-"}
        </Text>
      ),
    },
  ];

  const refColumns = [
    {
      title: "코드",
      dataIndex: "code",
      width: 70,
      render: (v: string) => {
        const groupKey = v.charAt(0).toUpperCase();
        return <Tag color={GROUP_LABELS[groupKey]?.color}>{v}</Tag>;
      },
    },
    {
      title: "분류",
      dataIndex: "code",
      width: 100,
      render: (v: string) => {
        const groupKey = v.charAt(0).toUpperCase();
        return <Text>{GROUP_LABELS[groupKey]?.label || "-"}</Text>;
      },
    },
    {
      title: "항목명",
      dataIndex: "name",
      width: 240,
      render: (v: string) => (
        <Text style={{ whiteSpace: "pre-wrap", wordBreak: "keep-all" }}>{v}</Text>
      ),
    },
    {
      title: "판정 기준",
      dataIndex: "criteria",
      render: (v: string) => (
        <Text style={{ whiteSpace: "pre-wrap", wordBreak: "keep-all" }}>{v}</Text>
      ),
    },
    {
      title: "기본 등급",
      dataIndex: "level",
      width: 90,
      render: (v: string) => {
        const cfg = SEVERITY_CONFIG[v] || SEVERITY_CONFIG.safe;
        return <Tag color={cfg.color}>{cfg.label}</Tag>;
      },
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <Alert
        title={
          <span>
            종합 위험도:{" "}
            <Tag color={riskConfig.color} style={{ fontSize: 14 }}>
              {riskConfig.label.toUpperCase()}
            </Tag>
          </span>
        }
        description={poison.summary}
        type={
          poison.risk_level === "danger"
            ? "error"
            : poison.risk_level === "warning"
              ? "warning"
              : "info"
        }
        showIcon
      />

      {poison.items && poison.items.length > 0 && (
        <Table<PoisonItem>
          columns={itemColumns}
          dataSource={poison.items}
          rowKey={(_, i) => String(i)}
          size="small"
          pagination={false}
          tableLayout="fixed"
        />
      )}

      <Collapse
        size="small"
        items={[
          {
            key: "ref",
            label: "독소조항 카테고리 정의 (A1~F3)",
            children: (
              <Table
                columns={refColumns}
                dataSource={POISON_CATEGORIES}
                rowKey="code"
                size="small"
                pagination={false}
                tableLayout="fixed"
              />
            ),
          },
        ]}
      />
    </div>
  );
}
