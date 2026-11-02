"""재무제표 항목 → 표준 키로 매핑. account_id(XBRL 표준계정) 우선, 없으면 계정명으로 매칭.

주의: fnlttSinglAcntAll 응답은 CFS(연결)와 OFS(별도)가 섞여 올 수 있으므로 호출 시 fs_div 를 지정하고,
연결이 없는 회사만 별도로 대체한다 (7월 M&A 모델 대화에서 확인한 함정).
"""
from __future__ import annotations

import re

# 표준 키: (account_id 후보들, 계정명 후보들(부분일치))
MAP: dict[str, tuple[list[str], list[str]]] = {
    "revenue": (["ifrs-full_Revenue", "ifrs_Revenue"], ["매출액", "매출", "영업수익"]),
    "cogs": (["ifrs-full_CostOfSales", "ifrs_CostOfSales"], ["매출원가"]),
    "gross": (["ifrs-full_GrossProfit", "ifrs_GrossProfit"], ["매출총이익"]),
    "sga": ([], ["판매비와관리비", "판매비및관리비"]),
    "op": (["dart_OperatingIncomeLoss"], ["영업이익"]),
    "pretax": (["ifrs-full_ProfitLossBeforeTax", "ifrs_ProfitLossBeforeTax"], ["법인세비용차감전순이익", "법인세차감전 순이익", "법인세비용차감전"]),
    "tax": (["ifrs-full_IncomeTaxExpenseContinuingOperations", "ifrs_IncomeTaxExpenseContinuingOperations"], ["법인세비용"]),
    "ni": (["ifrs-full_ProfitLoss", "ifrs_ProfitLoss"], ["당기순이익"]),
    "ni_owner": (["ifrs-full_ProfitLossAttributableToOwnersOfParent", "ifrs_ProfitLossAttributableToOwnersOfParent"], ["지배기업 소유주지분", "지배기업소유주지분", "지배기업의 소유주"]),
    "assets": (["ifrs-full_Assets", "ifrs_Assets"], ["자산총계"]),
    "cur_assets": (["ifrs-full_CurrentAssets", "ifrs_CurrentAssets"], ["유동자산"]),
    "cash": (["ifrs-full_CashAndCashEquivalents", "ifrs_CashAndCashEquivalents"], ["현금및현금성자산"]),
    "st_fin": (["ifrs-full_ShorttermDepositsNotClassifiedAsCashEquivalents", "dart_ShortTermDepositsNotClassifiedAsCashEquivalents"], ["단기금융상품"]),
    "receivables": (["ifrs-full_TradeAndOtherCurrentReceivables", "ifrs_TradeAndOtherCurrentReceivables"], ["매출채권및기타채권", "매출채권"]),
    "inventories": (["ifrs-full_Inventories", "ifrs_Inventories"], ["재고자산"]),
    "ppe": (["ifrs-full_PropertyPlantAndEquipment", "ifrs_PropertyPlantAndEquipment"], ["유형자산"]),
    "intangibles": (["ifrs-full_IntangibleAssetsOtherThanGoodwill", "ifrs_IntangibleAssetsOtherThanGoodwill"], ["무형자산"]),
    "liabilities": (["ifrs-full_Liabilities", "ifrs_Liabilities"], ["부채총계"]),
    "cur_liab": (["ifrs-full_CurrentLiabilities", "ifrs_CurrentLiabilities"], ["유동부채"]),
    "st_borrow": (["ifrs-full_CurrentLoansReceivedAndCurrentPortionOfNoncurrentLoansReceived", "ifrs-full_ShorttermBorrowings", "ifrs_ShortTermBorrowings"], ["단기차입금"]),
    "cur_lt_borrow": (["ifrs-full_CurrentPortionOfLongtermBorrowings", "dart_CurrentPortionOfLongTermBorrowings"], ["유동성장기차입금", "유동성장기부채"]),
    "lt_borrow": (["ifrs-full_LongtermBorrowings", "ifrs_LongTermBorrowings"], ["장기차입금"]),
    "bonds": (["ifrs-full_BondsIssued", "dart_BondsIssued"], ["사채"]),
    "equity": (["ifrs-full_Equity", "ifrs_Equity"], ["자본총계"]),
    "equity_owner": (["ifrs-full_EquityAttributableToOwnersOfParent", "ifrs_EquityAttributableToOwnersOfParent"], ["지배기업의 소유주에게 귀속되는 자본", "지배기업소유주지분"]),
    "capital": (["ifrs-full_IssuedCapital", "ifrs_IssuedCapital"], ["자본금"]),
    "retained": (["ifrs-full_RetainedEarnings", "ifrs_RetainedEarnings"], ["이익잉여금"]),
    "ocf": (["ifrs-full_CashFlowsFromUsedInOperatingActivities", "ifrs_CashFlowsFromUsedInOperatingActivities"], ["영업활동현금흐름", "영업활동으로인한현금흐름"]),
    "icf": (["ifrs-full_CashFlowsFromUsedInInvestingActivities", "ifrs_CashFlowsFromUsedInInvestingActivities"], ["투자활동현금흐름", "투자활동으로인한현금흐름"]),
    "fcf_fin": (["ifrs-full_CashFlowsFromUsedInFinancingActivities", "ifrs_CashFlowsFromUsedInFinancingActivities"], ["재무활동현금흐름", "재무활동으로인한현금흐름"]),
    "capex_ppe": (["ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities", "ifrs_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"], ["유형자산의 취득", "유형자산의취득"]),
    "capex_intangible": (["ifrs-full_PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities", "ifrs_PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities"], ["무형자산의 취득", "무형자산의취득"]),
    "dividends_paid": (["ifrs-full_DividendsPaidClassifiedAsFinancingActivities", "ifrs_DividendsPaidClassifiedAsFinancingActivities"], ["배당금지급", "배당금의 지급"]),
    "interest_paid": (["ifrs-full_InterestPaidClassifiedAsOperatingActivities"], ["이자의 지급", "이자지급"]),
    "eps": (["ifrs-full_BasicEarningsLossPerShare", "ifrs_BasicEarningsLossPerShare"], ["기본주당이익", "기본주당순이익"]),
}

# 손익 항목은 IS 가 없으면 CIS 에서 찾음. 재무상태표 항목은 BS 만.
SJ_FOR = {k: ("IS", "CIS") for k in ["revenue", "cogs", "gross", "sga", "op", "pretax", "tax", "ni", "ni_owner", "eps"]}
for k in ["assets", "cur_assets", "cash", "st_fin", "receivables", "inventories", "ppe", "intangibles", "liabilities", "cur_liab", "st_borrow", "cur_lt_borrow", "lt_borrow", "bonds", "equity", "equity_owner", "capital", "retained"]:
    SJ_FOR[k] = ("BS",)
for k in ["ocf", "icf", "fcf_fin", "capex_ppe", "capex_intangible", "dividends_paid", "interest_paid"]:
    SJ_FOR[k] = ("CF",)


def to_num(s) -> float | None:
    if s is None:
        return None
    t = str(s).replace(",", "").strip()
    if t in ("", "-"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def _norm(s: str) -> str:
    return re.sub(r"[\s()\[\]·,]", "", s or "")


def pick(items: list[dict], key: str) -> dict | None:
    """표준 키에 해당하는 행 하나 선택. account_id 일치 → 계정명 정확 일치 → 계정명 부분 일치."""
    ids, names = MAP[key]
    sjs = SJ_FOR.get(key, ("BS", "IS", "CIS", "CF"))
    cands = [it for it in items if it.get("sj_div") in sjs]
    for sj in sjs:  # IS 먼저, 없으면 CIS
        rows = [it for it in cands if it.get("sj_div") == sj]
        if not rows:
            continue
        for aid in ids:
            for it in rows:
                if it.get("account_id") == aid:
                    return it
        for nm in names:
            for it in rows:
                if _norm(it.get("account_nm")) == _norm(nm):
                    return it
        for nm in names:
            for it in rows:
                if _norm(nm) in _norm(it.get("account_nm")) and not _norm(it.get("account_nm")).startswith("비지배"):
                    return it
    return None


def extract_filing(items: list[dict], bsns_year: int) -> dict[int, dict]:
    """한 사업보고서(3개 기간) 응답 → {연도: {표준키: 값(원)}}"""
    out = {bsns_year: {}, bsns_year - 1: {}, bsns_year - 2: {}}
    for key in MAP:
        it = pick(items, key)
        if not it:
            continue
        for col, yr in (("thstrm_amount", bsns_year), ("frmtrm_amount", bsns_year - 1), ("bfefrmtrm_amount", bsns_year - 2)):
            v = to_num(it.get(col))
            if v is not None:
                out[yr][key] = v
    return out


def merge_years(filings: list[dict[int, dict]]) -> dict[int, dict]:
    """여러 보고서를 합침. 같은 연도는 더 최신 보고서(앞쪽) 값 우선."""
    merged: dict[int, dict] = {}
    for f in filings:
        for yr, d in f.items():
            m = merged.setdefault(yr, {})
            for k, v in d.items():
                m.setdefault(k, v)
    return merged
