from __future__ import annotations

import sqlite3
import re
from dataclasses import dataclass, fields, replace
from datetime import UTC, date, datetime
from functools import lru_cache
from types import MappingProxyType
from typing import Literal, Mapping

from ..checks import EvidenceRefusal
from ..ingest import (
    expected_partition_manifest,
    ingest_dataset_delivery_partitions,
    ingest_dataset_observation_partition_links,
    ingest_dataset_observations,
    ingest_dataset_versions,
    ingest_datasets,
    ingest_entities,
    ingest_items,
    ingest_payload_schemas,
    ingest_rights,
    ingest_source_records,
    ingest_spans,
    received_partition_manifest,
    reconstruction_manifest,
)
from ..model import (
    JSONValue,
    DatasetDeliveryPartitionRecord,
    DatasetObservationPartitionLinkRecord,
    DatasetObservationRecord,
    DatasetRecord,
    DatasetSliceRequest,
    DatasetVersionRecord,
    EntityRecord,
    EvidenceItemRecord,
    EvidenceRightRecord,
    EvidenceSpanRecord,
    PayloadSchemaRecord,
    SnapshotBundle,
    SnapshotBundleRequest,
    SourceRecordRecord,
    canonical_bytes,
    normalize_utc,
    sha256,
    validate_identifier,
    with_machine_id,
)
from ..schema import schema_digest
from ..snapshot import as_known_bundle
from ..terms import (
    P4AccessContext,
    P4_POSITIVE_ENTITY_RECORDS,
    P4ProjectionKind,
    P4_SCENARIO_DATASETS,
    validate_p4_positive_bundle_request,
)

P4_PROJECTION_KINDS = tuple(P4ProjectionKind.__args__)

P4_DOCUMENT_DATASETS = MappingProxyType(
    {
        "document:p4-public-liquid-prospectus": (
            "dataset:p4-doc-public-liquid-prospectus",
            "public",
            "public-terms-research",
        ),
        "document:p4-segregated-ima": (
            "dataset:p4-doc-segregated-ima",
            "segregated-mandate",
            "segregated-terms-governance",
        ),
        "document:p4-private-ppm": (
            "dataset:p4-doc-private-ppm",
            "pre-hire-public",
            "prehire-terms-research",
        ),
        "document:p4-whole-fund-lpa": (
            "dataset:p4-doc-whole-fund-lpa",
            "funded-commingled",
            "commingled-terms-monitoring",
        ),
        "document:p4-deal-by-deal-lpa": (
            "dataset:p4-doc-deal-by-deal-lpa",
            "funded-private-partnership",
            "private-terms-governance",
        ),
        "document:p4-amendment": ("dataset:terms", "shortlisted-nda", "research"),
        "document:p4-side-letter": (
            "dataset:p4-doc-side-letter",
            "funded-private-partnership",
            "private-side-letter-governance",
        ),
    }
)

P4_NEGATIVE_DATASET = (
    "dataset:p4-negative-terms",
    "shortlisted-nda",
    "negative-fixture-validation",
)
P4_METHOD_POLICY_DATASET = (
    "dataset:p4-method-boundary-policy",
    "public",
    "public-method-boundary",
)
P4_TERMS_DATASETS = (
    *(row[0] for row in P4_DOCUMENT_DATASETS.values()),
    *(row[0] for row in P4_SCENARIO_DATASETS.values()),
    P4_NEGATIVE_DATASET[0],
    P4_METHOD_POLICY_DATASET[0],
)

P4_TERMS_CUTOFFS = MappingProxyType(
    {
        "early": datetime(2024, 1, 31, 23, 59, 59, tzinfo=UTC),
        "amended": datetime(2024, 4, 30, 23, 59, 59, tzinfo=UTC),
        "side-letter": datetime(2024, 7, 31, 23, 59, 59, tzinfo=UTC),
    }
)
_P4_ACCESS_CONTEXTS: tuple[P4AccessContext, ...] = (
    "public",
    "pre-hire-public",
    "shortlisted-nda",
    "funded-commingled",
    "funded-private-partnership",
    "segregated-mandate",
)
P4_TERMS_BUNDLE_CASES = tuple(
    f"{cutoff_name}:{access_context}"
    for cutoff_name in P4_TERMS_CUTOFFS
    for access_context in _P4_ACCESS_CONTEXTS
)
P4_METHOD_POLICY_BUNDLE_CASE_ID = "method-policy:public"

P4_TERMS_DOCUMENT_IDS = (
    "document:p4-public-liquid-prospectus",
    "document:p4-segregated-ima",
    "document:p4-private-ppm",
    "document:p4-whole-fund-lpa",
    "document:p4-deal-by-deal-lpa",
    "document:p4-amendment",
    "document:p4-side-letter",
)

P4_POSITIVE_CASE_IDS = (
    "p4-p1",
    "p4-p2",
    "p4-p3",
    "p4-p4",
    "p4-p5",
    "p4-p6",
    "p4-p7",
    "p4-p8",
    "p4-p9a",
    "p4-p9b",
    "p4-p10",
    "p4-p11",
    "p4-p12",
    "p4-p13",
    "p4-p14",
    "p4-p15",
    "p4-p16",
    "p4-p17",
    "p4-p18",
    "p4-p19",
    "p4-p20",
    "p4-p21",
    "p4-p22",
    "p4-p23",
    "p4-p24",
    "p4-p25",
    "p4-p26",
    "p4-p27",
    "p4-p28a",
    "p4-p28b",
    "p4-p28c",
    "p4-p29a",
    "p4-p29b",
    "p4-p29c",
    "p4-p30",
    "p4-p30b",
    "p4-p30c",
    "p4-p31",
    "p4-p32",
    "p4-p33",
    "p4-p34",
    "p4-p35",
    "p4-p36",
)
P4_P1_SCENARIO_IDS = (
    "p4-p1-opening-nav",
    "p4-p1-daily-nav",
    "p4-p1-weighted-average-nav",
    "p4-p1-committed-capital",
    "p4-p1-invested-capital",
)
P4_POSITIVE_SCENARIO_IDS = (
    *P4_P1_SCENARIO_IDS,
    *(case_id for case_id in P4_POSITIVE_CASE_IDS if case_id != "p4-p1"),
)
P4_SCENARIO_FAMILY_BY_ID = MappingProxyType(
    {
        **{scenario_id: "p4-p1" for scenario_id in P4_P1_SCENARIO_IDS},
        **{case_id: case_id for case_id in P4_POSITIVE_CASE_IDS if case_id != "p4-p1"},
    }
)

P4_LIQUID_SCENARIO_IDS = (
    *P4_P1_SCENARIO_IDS,
    "p4-p2",
    "p4-p3",
    "p4-p4",
    "p4-p5",
    "p4-p6",
    "p4-p7",
    "p4-p8",
    "p4-p9a",
    "p4-p9b",
    "p4-p16",
    "p4-p17",
    "p4-p18",
    "p4-p19",
    "p4-p20",
    "p4-p21",
    "p4-p22",
    "p4-p23",
    "p4-p31",
    "p4-p33",
    "p4-p34",
    "p4-p36",
)
P4_CLOSED_SCENARIO_IDS = (
    "p4-p10",
    "p4-p11",
    "p4-p12",
    "p4-p13",
    "p4-p14",
    "p4-p15",
    "p4-p24",
    "p4-p25",
    "p4-p26",
    "p4-p27",
    "p4-p28a",
    "p4-p28b",
    "p4-p28c",
    "p4-p29a",
    "p4-p29b",
    "p4-p29c",
    "p4-p30",
    "p4-p30b",
    "p4-p30c",
    "p4-p31",
    "p4-p32",
    "p4-p33",
    "p4-p34",
    "p4-p35",
)
P4_SCENARIO_CONTEXTS = MappingProxyType(
    {
        "public": P4_LIQUID_SCENARIO_IDS,
        "pre-hire-public": P4_LIQUID_SCENARIO_IDS,
        "shortlisted-nda": P4_POSITIVE_SCENARIO_IDS,
        "funded-commingled": P4_LIQUID_SCENARIO_IDS,
        "funded-private-partnership": P4_CLOSED_SCENARIO_IDS,
        "segregated-mandate": P4_LIQUID_SCENARIO_IDS,
    }
)

_P4_SCENARIO_CONTROLLED_VALUES = MappingProxyType(
    {
        "p4-p1-opening-nav": ("base=opening-nav;m=.036;days=10 actual/360;opening_nav=1000", "management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=opening-nav"),
        "p4-p1-daily-nav": ("base=daily-nav;m=.036;days=10 actual/360;daily_nav=900 for days1-5,1100 for days6-10", "weighted_average_nav=1000;management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=daily-nav"),
        "p4-p1-weighted-average-nav": ("base=weighted-average-nav;m=.036;days=10 actual/360;weighted_average_nav=1000", "management_fee=1.00;base_substitution=false", "management_fee=1.00;projection_set=weighted-average-nav"),
        "p4-p1-committed-capital": ("base=committed-capital;m=.036;days=10 actual/360;committed_capital=1200", "management_fee=1.20;base_substitution=false", "management_fee=1.20;projection_set=committed-capital"),
        "p4-p1-invested-capital": ("base=invested-capital;m=.036;days=10 actual/360;invested_capital=800", "management_fee=.80;base_substitution=false", "management_fee=.80;projection_set=invested-capital"),
        "p4-p2": ("2023-01-31->2023-02-01:3650*.01*1 actual/365-fixed;2023-01-31->2023-03-02:900*.02*30 actual/360;2023-01-15->2023-02-15:1200*.03*30 30/360-US;2023-12-31->2024-01-01:36500*.01*1/365;2024-02-29->2024-03-01:36600*.01*1/366 ISDA", "day_count_fees=.10,1.50,3.00,1.00,1.00;ISDA_parts=1.00+1.00;ISDA_sum=2.00", "day_count_fees=.10,1.50,3.00,1.00,1.00;year_split_sum=parts"),
        "p4-p3": ("H=105;K=104;V*=110;p=.20;hurdle=hard;combination=max", "T=max(H,K)=105;E=V*-T=5;P=pE=1", "T=105;E=5;P=1"),
        "p4-p4": ("H=103;K=105;V*=110;p=.20;hurdle=hard;combination=max", "T=max(H,K)=105;E=V*-T=5;P=pE=1", "T=105;E=5;P=1"),
        "p4-p5": ("H=105;O=100;K=104;V*=110;p=.20;hurdle=hard;combination=additive", "T=H+(K-O)=109;E=V*-T=1;P=.20;absolute_level_double_count=false", "T=109;E=1;P=.20"),
        "p4-p6": ("prior_threshold=P4-P5-T109;V*=114;p=.20;soft_bases=gain-over-hwm,gain-over-opening-nav,projected-C8", "after_crossing_E=5,10,8;P=1,2,1.6", "at_or_below_threshold_E=0;P=0"),
        "p4-p7": ("path=P4-P3;H=105;V*=110;P=1;update_clauses=post-fee,pre-fee;valuation=interim,crystallization", "post_fee_H_next=109;pre_fee_H_next=110;interim_H_next=105", "next_history_opening_H=exact_prior_close"),
        "p4-p8": ("series_A=100->110,H=100;series_B_new=105->110,H=105;p=.20;hurdle=none", "fee_A=2;fee_B=1;aggregate_fee=3;subscription_profit=0", "each_series_NAV_identity=exact;aggregate_NAV_identity=exact"),
        "p4-p9a": ("fund_fee=2;raw_liability_legacy=1.50;raw_liability_subscriber=1.00;subscriber_credit=.50;direction=credit", "final_liability_legacy=1.50;subscriber=.50;aggregate=2", "subscription_profit=0;series_and_aggregate_tie"),
        "p4-p9b": ("fund_fee=2;raw_liability_legacy=1.50;raw_liability_subscriber=0;subscriber_debit=.50;direction=debit", "final_liability_legacy=1.50;subscriber=.50;aggregate=2", "subscription_profit=0;series_and_aggregate_tie"),
        "p4-p10": ("deal=A;eligible_fee_amount=10;offset_rate=.80;liability_before=12;beneficiary=LP;one_fee_offset_event=after-contribution-realization-writeoff-before-reserve-preferred-tiers", "offset_benefit=8;liability_after=4;D_g_unchanged_without_contribution", "closing_liability_A=4;aggregate=4;next_opening_A=4;next_opening_aggregate=4;later_offset_event=false"),
        "p4-p11": ("typed_cash_lot=deal-A120;D_g=120;reserve_target=20;fee_offset=none;clawback=none;tiers_LP=90,GP=10", "reserve_line=A/source-lot,vehicle,20;tiers_consume=100;unrounded_identity=120=20+90+10", "reserve_settled_total=20;settled_allocated_total=120;cash_rounding_residual=0;reserve_common_settlement_count=1"),
        "p4-p12": ("D_g=120;reserve=none;clawback=none;gross_tiers_LP=100,GP=20;escrow_rate=.25", "LP=100;GP_gross=20;GP_paid=15;carry_escrow=5", "identity=120=100+15+5;GP_gross=20"),
        "p4-p13": ("opening_settled_cash_paid_lots=A-old18,B-old12;returned=0;prior_hypothetical_GP_paid=30;current_GP_allocation_bridge=A-current10;settled_permitted_ceiling=cZ_cash30;path_authored_current_lot=false", "opening_and_current_lot_layers_tie_per_deal_and_aggregate;Gnet_cash=40;cash_obligation_C=10;reverse_attribution=A-current10;obligations_A=10,B=0", "current_D_g_identity=unchanged;economic_entitlement_layer=unchanged;closing_to_next_opening_lots=exact"),
        "p4-p14": ("holdback=none;G0=0;L0=20;c=.20;g=1;cash>=5", "Y*=5;GP=5;cumulative_GP_share=5/25=.20", "GP=5;LP=0;full_catchup_complete"),
        "p4-p15": ("G0=0;L0=1;c=.20;g=.80;cash>entitlement", "Y*=1/3 at policy precision;GP=4/15;LP=1/15", "GP=4/15;LP=1/15;pre_settlement_rounding=false"),
        "p4-p16": ("amount=100 USD;rate=.80 EUR per USD;direction=direct;fixing=matching", "converted=80 EUR;conversion_count=1", "converted=80 EUR;declared_stage_count=1"),
        "p4-p17": ("amount=100 USD;rate=1.25 USD per EUR;direction=inverse;fixing=matching", "converted=80 EUR;conversion_count=1", "converted=80 EUR;declared_stage_count=1"),
        "p4-p18": ("baseline=100;counterfactual=105;absolute_threshold=5;equality_is_outside=false,true", "signed_delta=5;absolute_delta=5", "equality_false=inside;equality_true=outside"),
        "p4-p19": ("prior_H=120;crystallization_V*=110;P=2;reset=perpetual,periodic-post-fee", "perpetual_H_close=120;periodic_H_close=108", "next_opening_H=selected_exact_close"),
        "p4-p20": ("O=100;opening_clock=2026-01-01;crystallization=2026-07-01;post_fee_NAV=108;reset=never,each-crystallization-post-NAV", "never_O=100,clock=2026-01-01;each_O=108,clock=2026-07-01", "next_opening_base_and_clock=selected_exact_close"),
        "p4-p21": ("unitized:u0=10,hu=10,flow=+2units;cash-additive:H=100,subscription=20,redemption=5;none:flows=0", "unitized_H_close=120;cash_additive_H_close=115;none_H_close=100", "none_with_nonzero_flow=refuse"),
        "p4-p22": ("H=105;K=104;O=100;V*=110;p=.20;hurdle=soft;combination=max;base=gain-over-opening-NAV", "T=105;activated_base=10;P=2", "at_V*=105:P=0"),
        "p4-p23": ("same_profitable_interim_and_close;rules=event-only-date,period-end;events=named,unnamed", "interim_event_only_fee_and_HWM=unchanged;named_event_crystallizes_once;period_end_crystallizes_once", "each_crystallization_appends=one_state_transition"),
        "p4-p24": ("bases=opening-capital100,unreturned-contributions100;simple=.10*1 ACT/365 year;compound=.10*2 ACT/365 years;segments=30 days ACT/360,30 days 30/360-US,leap-year ISDA", "simple_accrual=10;compound_cumulative=21;each_segment=canonical_day_count_fraction;closing_preferred=opening_preferred+accrual", "simple_accrual=10;compound_cumulative=21;all_segment_amounts_settle_from_full_precision;closing_preferred_identity=exact"),
        "p4-p25": ("D=150;capital=100;preferred=8;c=.20;g=1;residual=40;typed_ordered_cash_lots=A105,B45;reserve=none", "aggregate_LP=140;aggregate_GP=10;per_deal_A=105,B=45;aggregate_cash_and_share_tie", "A:capital_LP100+preferred_LP5;B:preferred_LP3+catchup_GP2+residual_LP32+residual_GP8;every_line_has_cash_lot_and_deal"),
        "p4-p26": ("scope=deal-by-deal;deal_A:D=60,capital=40,preferred=4,c=.20,g=1,residual=15", "deal_A_LP=40+4+12=56;deal_A_GP=1+3=4", "every_line_deal=A;deal_B_balances=unchanged"),
        "p4-p27": ("preferred=8;post_capital_cash=50;c=.20;g=1;carried_profit_bases=including-preferred,excluding-preferred", "including:catchup=2,residual_GP=8;excluding:catchup=0,carryable=42,residual_GP=8.4", "each_basis_GP_share=.20_of_own_denominator"),
        "p4-p28a": ("scope=whole-fund;deals=A,B;eligible_fees_A=6,B=4;offset_rate=.80;opening_liabilities_A=7,B=5;aggregate_eligible_fee=10;aggregate_opening_liability=12;current_tiers_allocations_distributions=complete_before_offset;offset_timing=period-end-before-sole-closing-state", "offsets_A=4.8,B=3.2;closing_liabilities_A=2.2,B=1.8;aggregate_offset=8;aggregate_closing_liability=4;current_D_g_tiers_allocations_distributions=unchanged", "next_opening_liabilities_A=2.2,B=1.8;aggregate=4;next_opening_complete_deal_and_aggregate_state=prior_close"),
        "p4-p28b": ("scope=deal-by-deal;deals=A,B;eligible_fees_A=6,B=4;offset_rate=.80;opening_liabilities_A=7,B=5;aggregate_eligible_fee=10;aggregate_opening_liability=12;ordered_fee_offset_events=A,B;event_timing=after-distribution-before-sole-closing-state", "offsets_A=4.8,B=3.2;closing_liabilities_A=2.2,B=1.8;each_closing_deal_liability=sole_offset_liability_after;aggregate_offset=8;aggregate_closing_liability=4", "next_opening_liabilities_A=2.2,B=1.8;aggregate=4;next_opening_complete_deal_and_aggregate_state=prior_close;swapped_or_missing_deal_state=refuse-before-output"),
        "p4-p28c": ("opening_liabilities_A=7,B=5;eligible_fee_A=6;offset_rate_A=.80;eligible_fee_B=0;operative_entries_A=1,B=0", "A_offset=4.8;A_close=2.2;B_close=5;aggregate_open=12;aggregate_close=7.2", "second_A_entry_or_any_B_entry_or_B_drift_or_wrong_aggregate=refuse"),
        "p4-p29a": ("period=first;predecessor_request=null;prior_result=null;derived_predecessor_envelope=null;opening_inventory=empty;deal_A_cash_lot=120;new_reserve=20", "generated_A_reserve_lot_original=20,remaining=20;add_transition=0->20;tiers_consume=100", "closing_reserve_A=20;aggregate=20;inventory_sum=20"),
        "p4-p29b": ("period=second;source_closed_predecessor_scaffold=P4-P29a-exact-request;prior_result=P4-P29a;release_input_id=stable-A-release,economic=5,settled=5,lot=A,event=A,deal=A,projection=A;D0=100;new_reserve_B=10", "predecessor_and_current_bundles_verify_at_own_cutoffs;A_transition_economic_and_settled=20->15;release_cash_lot_A=5;D_g=105;B_add=0->10;tiers_consume=95", "next_opening_dual_layers=prior_close;closing_A=15,B=10;aggregate_reserve=25;deal_ownership_A=15,B=10"),
        "p4-p29c": ("period=third;source_closed_predecessor_scaffold=P4-P29b-exact-request;prior_result=P4-P29b;opening_A=15,B=10;release_A=15,B=4;D0=0;new_reserve=0", "predecessor_and_current_bundles_verify_at_own_cutoffs;A_transition=15->0;B_transition=10->6;D_g=19", "closing_inventory_retains_A=0,B=6;aggregate_reserve=6;next_opening_complete_state_and_fresh_metadata=exact"),
        "p4-p30": ("opening_stable_settled_cash_lots=A-paid20,B-escrow10;returned=0;current_GP_bridges=A-paid7.5,B-escrow2.5;settled_permitted_ceiling=30", "opening_dual_balances_tie;Gnet_cash=40;clawback=10;reverse_attribution=B-current2.5,A-current7.5", "next_partial_release_B=5;same_lot_id_source_lineage;both_layers_update_and_copy_exactly"),
        "p4-p30b": ("prior_A_paid_original=15;prior_B_escrow_original=11;historical_A_return=3,target=paid;opening_A_paid=12,returned=3;current_A_paid=7;current_B_return=2,target=escrow;Z=40;c=.20", "B_escrow=11->9,returned=0->2;closing_outstanding=28;C=20;reverse_walk=7,9,4", "obligations_A=11,B=9;prior_and_current_transitions_exact;per_deal_and_aggregate_tie"),
        "p4-p30c": ("prior_B_escrow_original_economic_and_settled=11;historical_return=2;opening_B_paid=0,escrow=9,returned=2;current_release_input_economic=5,settled=5;same_B_lot_event_deal_projection", "same_input_id_on_holdback_and_transition;closing_B_paid=5,escrow=4,returned=2,remaining=9;Gnet_cash_and_economic_entitlement=unchanged", "next_projection_copies_both_layers_exact_fingerprint_with_fresh_metadata"),
        "p4-p31": ("direct_rate=.80 EUR/USD;pre-tier_target_event=100;post-tier_target_allocation=25;final-output_target=10", "distinct_target_ids_convert_once_to=80,20,8", "wrong_or_missing_target_or_stage=refuse"),
        "p4-p32": ("minor=.01;ordered_cash_lots=A1.005,B1.005;primary_D=2.01;reserve_target=1.005;reserve_owner=A;modes=half-even,half-up,down;settlement_stage=common-final;edge_C_raw=.004;edge_D=2.014", "half-even=1.00+1.00,residual=.01;half-up=1.01+1.01,residual=-.01;down=1.00+1.00,residual=.01;A_economic_reserve=1.005;A_settled_reserve=1.00,1.01,1.00;reserve_settled_total=A_settled_reserve;C_settled=0,skip_residual_ownership;residual_owner=B_final_settled_positive_segment", "next_opening_copies_economic_and_settled_layers;release_cap=settled_cash;economic_release=ruled_economic_delta;residual_never_mutates_A_or_C"),
        "p4-p33": ("ordered_scenarios=baseline,counterfactual;canonical_controlled_values=100,105;each_scenario_and_result_linked_to_verified_basis;changed_dimension=controlled-value", "fresh_resolution_binds_both_scenario_and_projection_ids;identity_free_semantic_remainder=byte_equal;signed_delta=5", "missing_swapped_noncanonical_cross_cutoff_or_second_dimension=refuse-before-verdict"),
        "p4-p34": ("liquid_events=management-fee,performance-fee;closed_segments=reserve,capital,preferred,catchup,residual,carry-escrow;reserve_totals=zero,nonzero;residuals=liquid,closed;zero_settled_raw_line=P4-P32-C-.004", "liquid_deal_and_cash_lot_ids=null;liquid_reserve_total=0;closed_non_residual_inherits=marginal_cash_lot_and_deal;reserve_event=reserve;reserve_beneficiary=vehicle;reserve_count=once_in_reserve_settled_and_common_settled_totals;residual_inherits=final_settled_positive_segment_lot_and_deal", "wrong_kind_event_lot_deal_beneficiary_reserve_omission_reserve_double_count_or_residual_mutation=refuse"),
        "p4-p35": ("paths=P4-P25-two-deal,P4-P32-reserve,P4-P30c-stable-lot;snapshots=complete-aggregate-and-deal;nonzero_residual_variant=settlement-present", "aggregate_equals_deal_sum;event_links=exact;reserve_changes=canonically_consumed_cash_lot_deals_only;lot_create_release_return=one-stable-id-exact-before-after;closing_event=zero-change-terminal", "mutated_event_order_affected_deals_reserve_ownership_cash_lot_source_lot_id_source_balance_unaffected_row_aggregate_sum_continuity_settlement_presence_closing_lot_tuple_or_final_snapshot=refuse"),
        "p4-p36": ("management_fee=.506;performance_fee=.497;minor_unit=.01;mode=half-even;stage=final-settlement;residual_beneficiary=vehicle", "economic_gross_total=1.003;unrounded_allocated_total=1.003;settlement_target_total=1.00;economic_to_settlement_delta=-.003;management_line=.51;performance_line=.50;settled_allocated_total=1.01;cash_rounding_residual=-.01", "settled_identity=1.00=1.01-.01;settled_NAV_uses_settlement_target_total=1.00;vehicle_cash_residual_applied_once;sub_minor_delta_not_cash"),
    }
)

_P4_NEGATIVE_REFUSAL_FAMILIES = MappingProxyType(
    {
        "p4-l1-missing-source-version": "missing-source-version",
        "p4-l2-ambiguous-precedence": "ambiguous-precedence",
        "p4-l3-precedence-cycle": "precedence-cycle",
        "p4-l4-wrong-beneficiary": "wrong-beneficiary",
        "p4-l5-unexecuted-amendment": "unexecuted-amendment",
        "p4-l6-contextual-ppm-conflict": "contextual-ppm-conflict",
        "p4-l7-fee-basis-missing": "fee-basis-missing",
        "p4-l11-equalization-required": "equalization-required",
        "p4-l12-fee-order-undefined": "fee-order-undefined",
        "p4-l14-clawback-rule-missing": "clawback-rule-missing",
        "p4-l16-fx-quotation-missing": "fx-quotation-missing",
        "p4-l20-materiality-policy-missing": "materiality-policy-missing",
        "p4-l23-future-clause-leak": "future-clause-leak",
        "p4-l26-prior-carry-source-invalid": "prior-carry-source-invalid",
        "p4-l27-carry-lot-transition-invalid": "carry-lot-transition-invalid",
        "p4-l28-reserve-allocation-invalid": "reserve-allocation-invalid",
        "p4-l29a-reserve-settlement-invalid": "reserve-settlement-invalid",
        "p4-l29b-reserve-lot-transition-invalid": "reserve-lot-transition-invalid",
        "p4-l29c-predecessor-scaffold-invalid": "predecessor-scaffold-invalid",
    }
)

P4_AUTHORED_NEGATIVE_CASE_IDS = (
    "p4-l1-missing-source-version",
    "p4-l2-ambiguous-precedence",
    "p4-l3-precedence-cycle",
    "p4-l4-wrong-beneficiary",
    "p4-l5-unexecuted-amendment",
    "p4-l6-contextual-ppm-conflict",
    "p4-l7-fee-basis-missing",
    "p4-l11-equalization-required",
    "p4-l12-fee-order-undefined",
    "p4-l14-clawback-rule-missing",
    "p4-l16-fx-quotation-missing",
    "p4-l20-materiality-policy-missing",
    "p4-l23-future-clause-leak",
    "p4-l26-prior-carry-source-invalid",
    "p4-l27-carry-lot-transition-invalid",
    "p4-l28-reserve-allocation-invalid",
    "p4-l29a-reserve-settlement-invalid",
    "p4-l29b-reserve-lot-transition-invalid",
    "p4-l29c-predecessor-scaffold-invalid",
)
P4_TOPOLOGY_ADVERSARY_IDS = ("p4-auth-partial-document-authorization",)
P4_NEGATIVE_BUNDLE_CASES = (*P4_AUTHORED_NEGATIVE_CASE_IDS, *P4_TOPOLOGY_ADVERSARY_IDS)
P4_NEGATIVE_ENTITY_RECORDS = MappingProxyType(
    {
        case_id: (
            f"case:{case_id}",
            "analysis-case",
            f"Synthetic Negative Case {ordinal:02d}",
        )
        for ordinal, case_id in enumerate(P4_AUTHORED_NEGATIVE_CASE_IDS, start=1)
    }
)
P4_CANONICAL_ENTITY_IDS = (
    *(row[0] for row in P4_POSITIVE_ENTITY_RECORDS.values()),
    *(row[0] for row in P4_NEGATIVE_ENTITY_RECORDS.values()),
)
P4_PREDECESSOR_SCAFFOLD_IDS = (
    "scaffold:p4-p29b-from-p29a",
    "scaffold:p4-p29c-from-p29b",
)

TERMS_SHAPES = tuple(
    {
        "record_kind": kind.replace("_", "-"),
        "fields": (
            "record_key",
            "projection_kind",
            "classification",
            "source_text",
            "span_marker",
            "value",
        ),
    }
    for kind in P4_PROJECTION_KINDS
)

P4_TERMS_FIXTURE_ID = "p4-terms-authored-v1"
P4_TERMS_AUTHORED_CLOSURE_CONTRACT_VERSION = "p4-terms-authored-closure-v1"
P4_TERMS_DIGEST_STATUS = "reviewed-pinned"
P4_TERMS_AUTHORED_SCHEMA_SHA256 = (
    "43a0f22036e3e6b55fc15a05071e58d7771ff5546cedce7c4ee45155f38b0818"
)
P4_TERMS_AUTHORED_CLOSURE_SHA256 = (
    "545821af539f4e13d80e0d82265996a0eefb66379003e0688cf43e6b31b3afd2"
)
P4_TERMS_AUTHORED_MANIFEST_SHA256 = (
    "fe5f125446587bd087465f7e7702fcf2fa995876cfcd1b6a61d40f5662a06b9b"
)
_LOWER_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_P4_CASE_KINDS = frozenset({"positive", "negative", "method-policy", "expected-refusal"})
_P4_EVIDENCE_REFUSAL_OUTCOMES = frozenset(
    {
        "missing-evidence-right",
        "right-not-known",
        "access-context-mismatch",
        "licence-purpose-mismatch",
        "entitlement-not-active",
        "right-revoked",
        "right-superseded",
        "right-retention-forbidden",
        "incomplete-revision-chain",
        "incomplete-dataset-version",
        "partition-manifest-mismatch",
        "delta-predecessor-invalid",
        "bundle-source-duplicate",
        "join-key-undefined",
    }
)

_P4_DOCUMENT_CONTEXTS = MappingProxyType(
    {
        "document:p4-public-liquid-prospectus": ("public", "funded-commingled"),
        "document:p4-segregated-ima": ("shortlisted-nda", "segregated-mandate"),
        "document:p4-private-ppm": (
            "pre-hire-public",
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
        "document:p4-whole-fund-lpa": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
        "document:p4-deal-by-deal-lpa": (
            "shortlisted-nda",
            "funded-private-partnership",
        ),
        "document:p4-amendment": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
            "segregated-mandate",
        ),
        "document:p4-side-letter": (
            "shortlisted-nda",
            "funded-commingled",
            "funded-private-partnership",
        ),
    }
)

_P4_VERSION_LABELS = MappingProxyType(
    {
        "dataset:p4-doc-public-liquid-prospectus": ("v1-full",),
        "dataset:p4-doc-segregated-ima": ("v1-full", "v2-amendment-delta"),
        "dataset:p4-doc-private-ppm": ("v1-full",),
        "dataset:p4-doc-whole-fund-lpa": (
            "v1-full",
            "v2-amendment-delta",
            "v3-side-letter-delta",
        ),
        "dataset:p4-doc-deal-by-deal-lpa": (
            "v1-full",
            "v2-amendment-delta",
            "v3-side-letter-delta",
        ),
        "dataset:terms": ("v1-amendment-full",),
        "dataset:p4-doc-side-letter": ("v1-side-letter-full",),
        "dataset:p4-scenarios-public": ("v1-full",),
        "dataset:p4-scenarios-prehire": ("v1-full",),
        "dataset:p4-scenarios-shortlisted": (
            "v1-full",
            "v2-p29b-delta",
            "v3-p29c-delta",
        ),
        "dataset:p4-scenarios-funded-commingled": ("v1-full",),
        "dataset:p4-scenarios-funded-private": (
            "v1-full",
            "v2-p29b-delta",
            "v3-p29c-delta",
        ),
        "dataset:p4-scenarios-segregated": ("v1-full",),
        "dataset:p4-negative-terms": ("v1-full", "v2-future-leak-delta"),
        "dataset:p4-method-boundary-policy": ("v1-full",),
    }
)

_P4_DOCUMENTS_BY_CONTEXT = MappingProxyType(
    {
        context: tuple(
            document_id
            for document_id, contexts in _P4_DOCUMENT_CONTEXTS.items()
            if context in contexts
            and document_id
            not in {"document:p4-amendment", "document:p4-side-letter"}
        )
        for context in _P4_ACCESS_CONTEXTS
    }
)


def _freeze_contract_value(value):
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_contract_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_contract_value(item) for item in value)
    return value


def _require_sha256(value: str, field_name: str) -> None:
    if not _LOWER_HEX_SHA256.fullmatch(value):
        raise ValueError(f"{field_name} must be a lowercase 64-hex SHA-256 digest")


def _require_identifier(value: str, field_name: str) -> None:
    try:
        validate_identifier(value)
    except EvidenceRefusal as exc:
        raise ValueError(f"{field_name} must be a valid identifier") from exc


@dataclass(frozen=True)
class P4BundleCaseContract:
    case_id: str
    case_kind: Literal["positive", "negative", "method-policy", "expected-refusal"]
    cutoff_name: str
    access_context: str
    source_dataset_ids: tuple[str, ...]
    canonical_entity_ids: tuple[str, ...]
    request_digest: str
    expected_outcome: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_dataset_ids", tuple(self.source_dataset_ids))
        object.__setattr__(self, "canonical_entity_ids", tuple(self.canonical_entity_ids))
        _require_identifier(self.case_id, "case_id")
        if self.case_kind not in _P4_CASE_KINDS:
            raise ValueError("case_kind is not controlled")
        if self.cutoff_name not in P4_TERMS_CUTOFFS:
            raise ValueError("cutoff_name is not controlled")
        if self.access_context not in _P4_ACCESS_CONTEXTS:
            raise ValueError("access_context is not controlled")
        _require_sha256(self.request_digest, "request_digest")
        if (
            not self.source_dataset_ids
            or len(self.source_dataset_ids) != len(set(self.source_dataset_ids))
            or self.source_dataset_ids != tuple(sorted(self.source_dataset_ids))
            or not set(self.source_dataset_ids).issubset(P4_TERMS_DATASETS)
        ):
            raise ValueError("source_dataset_ids must be unique canonical P4 datasets")
        if (
            len(self.canonical_entity_ids) != len(set(self.canonical_entity_ids))
            or self.canonical_entity_ids != tuple(sorted(self.canonical_entity_ids))
            or not set(self.canonical_entity_ids).issubset(P4_CANONICAL_ENTITY_IDS)
            or (self.case_kind != "method-policy" and not self.canonical_entity_ids)
        ):
            raise ValueError("canonical_entity_ids must be canonical P4 entities")
        if self.case_kind in {"positive", "method-policy"}:
            if self.expected_outcome != "admitted":
                raise ValueError("admitted cases require the admitted outcome")
        elif self.case_kind == "negative":
            if self.expected_outcome not in {
                "bundle-admitted-for-card-refusal",
                *_P4_EVIDENCE_REFUSAL_OUTCOMES,
            }:
                raise ValueError("negative expected_outcome is not controlled")
        elif self.expected_outcome not in _P4_EVIDENCE_REFUSAL_OUTCOMES:
            raise ValueError("expected-refusal cases require an evidence refusal code")


@dataclass(frozen=True)
class P4TermsFixtureManifest:
    fixture_id: str
    fixture_digest: str
    schema_version: str
    schema_digest: str
    digest_status: str
    dataset_ids: tuple[str, ...]
    document_dataset_ids: tuple[str, ...]
    scenario_dataset_ids: tuple[str, ...]
    negative_dataset_id: str
    method_policy_dataset_id: str
    canonical_entity_ids: tuple[str, ...]
    canonical_entity_records: Mapping[str, tuple[object, ...]]
    document_ids: tuple[str, ...]
    right_ids: Mapping[str, str]
    right_records: Mapping[str, tuple[object, ...]]
    access_contexts: Mapping[str, str]
    licence_purposes: Mapping[str, str]
    cutoff_values: Mapping[str, str]
    version_ids: tuple[str, ...]
    version_records: Mapping[str, tuple[object, ...]]
    partition_records: Mapping[str, tuple[tuple[object, ...], ...]]
    payload_schema_ids: tuple[str, ...]
    payload_schema_digests: Mapping[str, str]
    source_record_ids: tuple[str, ...]
    evidence_item_ids: tuple[str, ...]
    evidence_span_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    source_content_digests: Mapping[str, str]
    reconstruction_digests: Mapping[str, str]
    projection_ids: tuple[str, ...]
    projection_counts: Mapping[str, int]
    projection_receipt_ids: Mapping[str, str]
    positive_case_ids: tuple[str, ...]
    scenario_ids: tuple[str, ...]
    scenario_family_by_id: Mapping[str, str]
    negative_case_ids: tuple[str, ...]
    topology_adversary_ids: tuple[str, ...]
    predecessor_scaffold_ids: tuple[str, ...]
    bundle_case_records: Mapping[str, P4BundleCaseContract]
    slice_receipt_ids: Mapping[str, str]
    slice_digests: Mapping[str, str]
    join_receipt_ids: Mapping[str, str]
    positive_bundle_digests: Mapping[str, str]
    negative_bundle_results: Mapping[str, tuple[str, str]]
    method_policy_bundle_digest: str
    pit_cases: Mapping[str, str]
    limitations: tuple[str, ...]
    current_attestation: str
    live_attestation_ceiling: str
    disclosure: str

    def __post_init__(self) -> None:
        for field in fields(self):
            object.__setattr__(
                self,
                field.name,
                _freeze_contract_value(getattr(self, field.name)),
            )
        for field_name in (
            "fixture_digest",
            "schema_digest",
            "method_policy_bundle_digest",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "payload_schema_digests",
            "source_content_digests",
            "reconstruction_digests",
            "slice_digests",
            "positive_bundle_digests",
        ):
            for key, digest in getattr(self, field_name).items():
                _require_sha256(digest, f"{field_name}[{key!r}]")


def _p4_right_scopes() -> dict[str, tuple[str, str]]:
    return {
        **{row[0]: row[1:] for row in P4_DOCUMENT_DATASETS.values()},
        **{
            row[0]: (context, row[1])
            for context, row in P4_SCENARIO_DATASETS.items()
        },
        P4_NEGATIVE_DATASET[0]: P4_NEGATIVE_DATASET[1:],
        P4_METHOD_POLICY_DATASET[0]: P4_METHOD_POLICY_DATASET[1:],
    }


def _p4_right_id(dataset_id: str) -> str:
    from .core import core_right_id

    if dataset_id == "dataset:terms":
        return core_right_id("terms")
    access_context, licence_purpose = _p4_right_scopes()[dataset_id]
    jan1 = datetime(2024, 1, 1, tzinfo=UTC)
    return with_machine_id(
        "right",
        EvidenceRightRecord(
            "",
            f"right-series:{dataset_id.removeprefix('dataset:')}",
            1,
            dataset_id,
            access_context,
            licence_purpose,
            "active",
            "retain-after-expiry",
            jan1,
            jan1,
            None,
        ),
    ).evidence_right_id


def _p4_positive_dataset_ids(
    *, cutoff_name: str, access_context: P4AccessContext
) -> tuple[str, ...]:
    if cutoff_name not in P4_TERMS_CUTOFFS or access_context not in P4_SCENARIO_DATASETS:
        raise EvidenceRefusal("p4-term-bundle-request-invalid")
    dataset_ids = [
        P4_DOCUMENT_DATASETS[document_id][0]
        for document_id in _P4_DOCUMENTS_BY_CONTEXT[access_context]
    ]
    cutoff_index = tuple(P4_TERMS_CUTOFFS).index(cutoff_name)
    if cutoff_index >= tuple(P4_TERMS_CUTOFFS).index("amended") and access_context in {
        "shortlisted-nda",
        "funded-commingled",
        "funded-private-partnership",
        "segregated-mandate",
    }:
        dataset_ids.append(P4_DOCUMENT_DATASETS["document:p4-amendment"][0])
    if cutoff_index >= tuple(P4_TERMS_CUTOFFS).index("side-letter") and access_context in {
        "shortlisted-nda",
        "funded-commingled",
        "funded-private-partnership",
    }:
        dataset_ids.append(P4_DOCUMENT_DATASETS["document:p4-side-letter"][0])
    dataset_ids.append(P4_SCENARIO_DATASETS[access_context][0])
    return tuple(sorted(dataset_ids))


def _p4_slice_request(
    dataset_id: str, *, canonical_entity_ids: tuple[str, ...], include_unresolved: bool
) -> DatasetSliceRequest:
    access_context, licence_purpose = _p4_right_scopes()[dataset_id]
    return DatasetSliceRequest(
        dataset_id=dataset_id,
        access_context=access_context,
        evidence_right_id=_p4_right_id(dataset_id),
        licence_purpose=licence_purpose,
        canonical_entity_ids=canonical_entity_ids,
        include_unresolved=include_unresolved,
    )


def _p4_schema_rows() -> tuple[PayloadSchemaRecord, ...]:
    string_array: dict[str, JSONValue] = {
        "type": "array",
        "items": {"type": "string"},
    }
    nullable_string: dict[str, JSONValue] = {"type": ["string", "null"]}
    common_properties: dict[str, JSONValue] = {
        "record_key": {"type": "string"},
        "classification": {
            "enum": [
                "authored-contract-evidence",
                "hypothetical-contract-scenario",
            ]
        },
        "source_text": {"type": "string", "minLength": 1},
        "span_marker": {"type": "string", "minLength": 1},
    }
    required = [
        "record_key",
        "projection_kind",
        "classification",
        "source_text",
        "span_marker",
        "value",
    ]
    rows = []
    for kind in P4_PROJECTION_KINDS:
        value_properties: dict[str, JSONValue] = {}
        value_required: list[str] = []
        if kind == "term_document":
            value_properties = {
                "document_id": {"type": "string"},
                "authorized_context": {"type": "string"},
            }
            value_required = ["document_id", "authorized_context"]
        elif kind == "term_clause":
            value_properties = {
                "document_key": {"type": "string"},
                "clause_id": {"type": "string"},
                "clause_family": {"type": "string"},
                "effective_from": {"type": "string"},
                "effective_to": nullable_string,
            }
            value_required = list(value_properties)
        elif kind == "term_relation":
            value_properties = {
                "document_key": {"type": "string"},
                "relation_id": {"type": "string"},
                "relation_type": {"type": "string"},
                "from_clause_key": {"type": "string"},
                "to_clause_key": {"type": "string"},
                "term_key": {"type": "string"},
                "investor_scope": string_array,
                "vehicle_scope": string_array,
                "effective_from": {"type": "string"},
                "effective_to": nullable_string,
                "review_state": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "scenario_input":
            value_properties = {
                "scenario_id": {"type": "string"},
                "scenario_family": {"type": "string"},
                "controlled_inputs": string_array,
                "calculation_policy_projection_key": nullable_string,
                "materiality_basis_projection_key": nullable_string,
                "dependency_projection_keys": string_array,
                "expected_full_precision": {"type": "string"},
                "expected_settlement_precision": {"type": "string"},
                "expected_refusal_family": nullable_string,
                "adversarial_source": nullable_string,
            }
            value_required = list(value_properties)
        elif kind == "calculation_policy":
            value_properties = {
                "policy_id": {"type": "string"},
                "policy_family": {"type": "string"},
                "engine": {"type": "string"},
                "calculation_precision": {"type": "string"},
                "ordered_event_kinds": string_array,
                "rounding_policy_projection_key": {"type": "string"},
                "effective_from": {"type": "string"},
                "effective_to": nullable_string,
            }
            value_required = list(value_properties)
        elif kind == "method_boundary_policy":
            value_properties = {
                "policy_id": {"type": "string"},
                "policy_family": {"type": "string"},
                "boundary_kind": {"type": "string"},
                "prohibited_actual_cash_source_classes": string_array,
                "refusal_claim_ids": string_array,
                "effective_from": {"type": "string"},
                "effective_to": nullable_string,
            }
            value_required = list(value_properties)
        elif kind == "predecessor_request_scaffold":
            value_properties = {
                "scaffold_id": {"type": "string"},
                "expected_predecessor_scenario_id": {"type": "string"},
                "predecessor_cutoff": {"type": "string"},
                "predecessor_source_dataset_ids": string_array,
                "predecessor_join_keys": string_array,
                "predecessor_join_policy": {"type": "string"},
                "predecessor_request_json": {"type": "string"},
                "predecessor_request_digest": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "prior_carry_event":
            value_properties = {
                "event_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "amount": {"type": "string"},
                "currency": {"type": "string"},
                "deal_id": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "prior_carry_allocation":
            value_properties = {
                "allocation_id": {"type": "string"},
                "event_projection_key": {"type": "string"},
                "amount": {"type": "string"},
                "beneficiary": {"type": "string"},
                "deal_id": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "prior_lot_transition":
            value_properties = {
                "transition_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "opening": {"type": "string"},
                "closing": {"type": "string"},
                "deal_id": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "opening_carry_lot":
            value_properties = {
                "lot_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "paid": {"type": "string"},
                "escrow": {"type": "string"},
                "returned": {"type": "string"},
                "deal_id": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "carry_return":
            value_properties = {
                "return_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "amount": {"type": "string"},
                "target_bucket": {"type": "string"},
                "deal_id": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "deal_cash_lot":
            value_properties = {
                "lot_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "amount": {"type": "string"},
                "deal_id": {"type": "string"},
                "source_event": {"type": "string"},
                "source_allocation_id": {"type": "string"},
                "currency": {"type": "string"},
                "economic_balance": {"type": "string"},
                "settled_balance": {"type": "string"},
                "continuity_order": {"type": "integer"},
            }
            value_required = ["lot_id", "lot_family", "amount", "deal_id", "source_event"]
        elif kind == "opening_reserve_lot":
            value_properties = {
                "lot_id": {"type": "string"},
                "lot_family": {"type": "string"},
                "original": {"type": "string"},
                "remaining": {"type": "string"},
                "source_cash_lot_id": {"type": "string"},
                "source_event_id": {"type": "string"},
                "source_allocation_id": {"type": "string"},
                "deal_id": {"type": "string"},
                "currency": {"type": "string"},
                "economic_balance": {"type": "string"},
                "settled_balance": {"type": "string"},
                "continuity_order": {"type": "integer"},
            }
            value_required = ["lot_id", "lot_family", "original", "remaining", "deal_id"]
        elif kind == "materiality_policy":
            value_properties = {
                "policy_id": {"type": "string"},
                "policy_family": {"type": "string"},
                "absolute_threshold": {"type": "string"},
                "equality_is_outside": {"type": "boolean"},
            }
            value_required = list(value_properties)
        elif kind == "materiality_comparison_basis":
            value_properties = {
                "basis_id": {"type": "string"},
                "baseline_scenario_id": {"type": "string"},
                "counterfactual_scenario_id": {"type": "string"},
                "changed_dimension": {"type": "string"},
            }
            value_required = list(value_properties)
        elif kind == "rounding_policy":
            value_properties = {
                "policy_id": {"type": "string"},
                "policy_family": {"type": "string"},
                "minor_unit": {"type": "string"},
                "mode": {"type": "string"},
                "stage": {"type": "string"},
            }
            value_required = list(value_properties)
        value_schema: dict[str, JSONValue] = {
            "type": "object",
            "properties": value_properties,
            "required": value_required,
            "additionalProperties": False,
        }
        schema: dict[str, JSONValue] = {
            "type": "object",
            "required": required,
            "properties": {
                **common_properties,
                "projection_kind": {"const": kind},
                "value": value_schema,
            },
            "additionalProperties": False,
        }
        rows.append(
            PayloadSchemaRecord(
                f"schema:p4-{kind.replace('_', '-')}-v1",
                kind.replace("_", "-"),
                schema,
                sha256(canonical_bytes(schema)),
            )
        )
    return tuple(rows)


def _p4_scenario_dependency_specs(
    context: str, scenario_id: str
) -> tuple[tuple[str, str, dict[str, JSONValue]], ...]:
    def row(
        key: str, kind: str, **value: JSONValue
    ) -> tuple[str, str, dict[str, JSONValue]]:
        return (f"{key}:{context}", kind, value)

    if scenario_id == "p4-p13":
        return (
            row("prior-carry-event:p4-p13:a-old", "prior_carry_event", event_id="event:p4-p13:a-old", lot_family="opening-carry", amount="18", currency="USD", deal_id="deal:A"),
            row("prior-carry-allocation:p4-p13:a-old", "prior_carry_allocation", allocation_id="allocation:p4-p13:a-old", event_projection_key=f"prior-carry-event:p4-p13:a-old:{context}", amount="18", beneficiary="GP", deal_id="deal:A"),
            row("opening-carry-lot:p4-p13:a-old", "opening_carry_lot", lot_id="lot:p4-p13:a-old", lot_family="opening-carry", paid="18", escrow="0", returned="0", deal_id="deal:A"),
            row("prior-carry-event:p4-p13:b-old", "prior_carry_event", event_id="event:p4-p13:b-old", lot_family="opening-carry", amount="12", currency="USD", deal_id="deal:B"),
            row("prior-carry-allocation:p4-p13:b-old", "prior_carry_allocation", allocation_id="allocation:p4-p13:b-old", event_projection_key=f"prior-carry-event:p4-p13:b-old:{context}", amount="12", beneficiary="GP", deal_id="deal:B"),
            row("opening-carry-lot:p4-p13:b-old", "opening_carry_lot", lot_id="lot:p4-p13:b-old", lot_family="opening-carry", paid="12", escrow="0", returned="0", deal_id="deal:B"),
            row("prior-lot-transition:p4-p13:a-current", "prior_lot_transition", transition_id="transition:p4-p13:a-current", lot_family="prior-transition", opening="0", closing="10", deal_id="deal:A"),
        )
    if scenario_id == "p4-p29a":
        return (
            row("deal-cash-lot:p4-p29a:a", "deal_cash_lot", lot_id="lot:p4-p29a:a-cash", lot_family="deal-cash", amount="120", deal_id="deal:A", source_event="event:p4-p29a:realization", source_allocation_id="allocation:p4-p29a:a-reserve", currency="USD", economic_balance="120", settled_balance="120", continuity_order=1),
        )
    if scenario_id == "p4-p29b":
        return (
            row("opening-reserve-lot:p4-p29b:a", "opening_reserve_lot", lot_id="lot:p4-p29a:a-reserve", lot_family="opening-reserve", original="20", remaining="20", source_cash_lot_id="lot:p4-p29a:a-cash", source_event_id="event:p4-p29a:realization", source_allocation_id="allocation:p4-p29a:a-reserve", deal_id="deal:A", currency="USD", economic_balance="20", settled_balance="20", continuity_order=2),
            row("prior-lot-transition:p4-p29b:a-release", "prior_lot_transition", transition_id="transition:p4-p29b:a-release", lot_family="prior-transition", opening="20", closing="15", deal_id="deal:A"),
            row("deal-cash-lot:p4-p29b:b", "deal_cash_lot", lot_id="lot:p4-p29b:b-cash", lot_family="deal-cash", amount="10", deal_id="deal:B", source_event="event:p4-p29b:reserve-add", source_allocation_id="allocation:p4-p29b:b-reserve", currency="USD", economic_balance="10", settled_balance="10", continuity_order=3),
            row("prior-lot-transition:p4-p29b:b-add", "prior_lot_transition", transition_id="transition:p4-p29b:b-add", lot_family="prior-transition", opening="0", closing="10", deal_id="deal:B"),
        )
    if scenario_id == "p4-p29c":
        return (
            row("opening-reserve-lot:p4-p29c:a", "opening_reserve_lot", lot_id="lot:p4-p29a:a-reserve", lot_family="opening-reserve", original="20", remaining="15", source_cash_lot_id="lot:p4-p29a:a-cash", source_event_id="event:p4-p29a:realization", source_allocation_id="allocation:p4-p29a:a-reserve", deal_id="deal:A", currency="USD", economic_balance="15", settled_balance="15", continuity_order=4),
            row("opening-reserve-lot:p4-p29c:b", "opening_reserve_lot", lot_id="lot:p4-p29b:b-reserve", lot_family="opening-reserve", original="10", remaining="10", source_cash_lot_id="lot:p4-p29b:b-cash", source_event_id="event:p4-p29b:reserve-add", source_allocation_id="allocation:p4-p29b:b-reserve", deal_id="deal:B", currency="USD", economic_balance="10", settled_balance="10", continuity_order=5),
            row("prior-lot-transition:p4-p29c:a-release", "prior_lot_transition", transition_id="transition:p4-p29c:a-release", lot_family="prior-transition", opening="15", closing="0", deal_id="deal:A"),
            row("prior-lot-transition:p4-p29c:b-release", "prior_lot_transition", transition_id="transition:p4-p29c:b-release", lot_family="prior-transition", opening="10", closing="6", deal_id="deal:B"),
        )
    if scenario_id == "p4-p30":
        return (
            row("prior-carry-event:p4-p30:a-old", "prior_carry_event", event_id="event:p4-p30:a-old", lot_family="opening-carry", amount="20", currency="USD", deal_id="deal:A"),
            row("prior-carry-allocation:p4-p30:a-old", "prior_carry_allocation", allocation_id="allocation:p4-p30:a-old", event_projection_key=f"prior-carry-event:p4-p30:a-old:{context}", amount="20", beneficiary="GP", deal_id="deal:A"),
            row("opening-carry-lot:p4-p30:a-paid", "opening_carry_lot", lot_id="lot:p4-p30:a-paid", lot_family="opening-carry", paid="20", escrow="0", returned="0", deal_id="deal:A"),
            row("prior-carry-event:p4-p30:b-old", "prior_carry_event", event_id="event:p4-p30:b-old", lot_family="opening-carry", amount="10", currency="USD", deal_id="deal:B"),
            row("prior-carry-allocation:p4-p30:b-old", "prior_carry_allocation", allocation_id="allocation:p4-p30:b-old", event_projection_key=f"prior-carry-event:p4-p30:b-old:{context}", amount="10", beneficiary="GP", deal_id="deal:B"),
            row("opening-carry-lot:p4-p30:b-escrow", "opening_carry_lot", lot_id="lot:p4-p30:b-escrow", lot_family="opening-carry", paid="0", escrow="10", returned="0", deal_id="deal:B"),
            row("prior-lot-transition:p4-p30:a-current", "prior_lot_transition", transition_id="transition:p4-p30:a-current", lot_family="prior-transition", opening="0", closing="7.5", deal_id="deal:A"),
            row("prior-lot-transition:p4-p30:b-current", "prior_lot_transition", transition_id="transition:p4-p30:b-current", lot_family="prior-transition", opening="0", closing="2.5", deal_id="deal:B"),
        )
    if scenario_id == "p4-p30b":
        return (
            row("prior-carry-event:p4-p30b:a-old", "prior_carry_event", event_id="event:p4-p30b:a-old", lot_family="opening-carry", amount="15", currency="USD", deal_id="deal:A"),
            row("prior-carry-allocation:p4-p30b:a-old", "prior_carry_allocation", allocation_id="allocation:p4-p30b:a-old", event_projection_key=f"prior-carry-event:p4-p30b:a-old:{context}", amount="15", beneficiary="GP", deal_id="deal:A"),
            row("opening-carry-lot:p4-p30b:a-paid", "opening_carry_lot", lot_id="lot:p4-p30b:a-paid", lot_family="opening-carry", paid="12", escrow="0", returned="3", deal_id="deal:A"),
            row("prior-carry-event:p4-p30b:b-old", "prior_carry_event", event_id="event:p4-p30b:b-old", lot_family="opening-carry", amount="11", currency="USD", deal_id="deal:B"),
            row("prior-carry-allocation:p4-p30b:b-old", "prior_carry_allocation", allocation_id="allocation:p4-p30b:b-old", event_projection_key=f"prior-carry-event:p4-p30b:b-old:{context}", amount="11", beneficiary="GP", deal_id="deal:B"),
            row("opening-carry-lot:p4-p30b:b-escrow", "opening_carry_lot", lot_id="lot:p4-p30b:b-escrow", lot_family="opening-carry", paid="0", escrow="11", returned="0", deal_id="deal:B"),
            row("carry-return:p4-p30b:a-historical", "carry_return", return_id="return:p4-p30b:a-historical", lot_family="carry-return", amount="3", target_bucket="paid", deal_id="deal:A"),
            row("prior-lot-transition:p4-p30b:a-current", "prior_lot_transition", transition_id="transition:p4-p30b:a-current", lot_family="prior-transition", opening="0", closing="7", deal_id="deal:A"),
            row("carry-return:p4-p30b:b-current", "carry_return", return_id="return:p4-p30b:b-current", lot_family="carry-return", amount="2", target_bucket="escrow", deal_id="deal:B"),
        )
    if scenario_id == "p4-p30c":
        return (
            row("prior-carry-event:p4-p30c:b-old", "prior_carry_event", event_id="event:p4-p30c:b-old", lot_family="opening-carry", amount="11", currency="USD", deal_id="deal:B"),
            row("prior-carry-allocation:p4-p30c:b-old", "prior_carry_allocation", allocation_id="allocation:p4-p30c:b-old", event_projection_key=f"prior-carry-event:p4-p30c:b-old:{context}", amount="11", beneficiary="GP", deal_id="deal:B"),
            row("opening-carry-lot:p4-p30c:b-escrow", "opening_carry_lot", lot_id="lot:p4-p30c:b-escrow", lot_family="opening-carry", paid="0", escrow="9", returned="2", deal_id="deal:B"),
            row("carry-return:p4-p30c:b-historical", "carry_return", return_id="return:p4-p30c:b-historical", lot_family="carry-return", amount="2", target_bucket="escrow", deal_id="deal:B"),
            row("prior-lot-transition:p4-p30c:b-release", "prior_lot_transition", transition_id="transition:p4-p30c:b-release", lot_family="prior-transition", opening="9", closing="4", deal_id="deal:B"),
        )

    specs: list[tuple[str, str, dict[str, JSONValue]]] = []
    if scenario_id in {
        "p4-p10", "p4-p11", "p4-p12", "p4-p14", "p4-p15", "p4-p24",
        "p4-p25", "p4-p26", "p4-p27", "p4-p28a", "p4-p28b", "p4-p28c",
        "p4-p32", "p4-p34", "p4-p35",
    }:
        specs.append(
            row(
                f"deal-cash-lot:{scenario_id}:a",
                "deal_cash_lot",
                lot_id=f"lot:{scenario_id}:A-cash",
                lot_family="deal-cash",
                amount="120",
                deal_id="deal:A",
                source_event=f"event:{scenario_id}:realization",
            )
        )
    if scenario_id in {"p4-p11", "p4-p32", "p4-p34", "p4-p35"}:
        specs.append(
            row(
                f"opening-reserve-lot:{scenario_id}:a",
                "opening_reserve_lot",
                lot_id=f"lot:{scenario_id}:A-reserve",
                lot_family="opening-reserve",
                original="20",
                remaining="20",
                deal_id="deal:A",
            )
        )
    return tuple(specs)


def _p4_scenario_dependency_keys(context: str, scenario_id: str) -> tuple[str, ...]:
    keys: list[str] = []
    if scenario_id in {"p4-p18", "p4-p33"}:
        keys.extend(
            (
                f"materiality-policy:{context}",
                f"materiality-basis:{scenario_id}:{context}",
            )
        )
    if scenario_id == "p4-p29b":
        keys.append(f"scaffold:p4-p29b-from-p29a:{context}")
    if scenario_id == "p4-p29c":
        keys.append(f"scaffold:p4-p29c-from-p29b:{context}")
    keys.extend(
        record_key
        for record_key, _, _ in _p4_scenario_dependency_specs(context, scenario_id)
    )
    return tuple(keys)


def _p4_source_specs() -> tuple[dict[str, object], ...]:
    specs: list[dict[str, object]] = []
    relation_rows = {
        "amends": ("document:p4-public-liquid-prospectus", "public", "2024-01-15"),
        "supersedes": ("document:p4-segregated-ima", "shortlisted-nda", "2024-04-15"),
        "clarifies": ("document:p4-private-ppm", "pre-hire-public", "2024-01-15"),
        "incorporates": ("document:p4-whole-fund-lpa", "funded-commingled", "2024-01-15"),
        "investor_override": ("document:p4-side-letter", "funded-private-partnership", "2024-07-15"),
    }
    for document_id, (dataset_id, right_context, _) in P4_DOCUMENT_DATASETS.items():
        for context in _P4_DOCUMENT_CONTEXTS[document_id]:
            specs.append(
                {
                    "dataset_id": dataset_id,
                    "source_record_key": f"{document_id}:{context}",
                    "source_entity_type": "document",
                    "projection_kind": "term_document",
                    "classification": "authored-contract-evidence",
                    "canonical_entity_id": P4_POSITIVE_ENTITY_RECORDS[context][0],
                    "right_context": right_context,
                    "value": {
                        "document_id": document_id,
                        "authorized_context": context,
                    },
                }
            )
    for relation_type, (document_id, context, received_at) in relation_rows.items():
        dataset_id, right_context, _ = P4_DOCUMENT_DATASETS[document_id]
        relation_slug = relation_type.replace("_", "-")
        clause_keys = (
            f"clause:{relation_slug}:source:{context}",
            f"clause:{relation_slug}:target:{context}",
        )
        for position, clause_key in zip(("source", "target"), clause_keys, strict=True):
            specs.append(
                {
                    "dataset_id": dataset_id,
                    "source_record_key": clause_key,
                    "source_entity_type": "clause",
                    "projection_kind": "term_clause",
                    "classification": "authored-contract-evidence",
                    "canonical_entity_id": P4_POSITIVE_ENTITY_RECORDS[context][0],
                    "right_context": right_context,
                    "received_at": received_at,
                    "value": {
                        "document_key": document_id,
                        "clause_id": clause_key,
                        "clause_family": f"{relation_slug}-{position}",
                        "effective_from": received_at,
                        "effective_to": None,
                    },
                }
            )
        specs.append(
            {
                "dataset_id": dataset_id,
                "source_record_key": f"relation:{relation_slug}:{context}",
                "source_entity_type": "relation",
                "projection_kind": "term_relation",
                "classification": "authored-contract-evidence",
                "canonical_entity_id": P4_POSITIVE_ENTITY_RECORDS[context][0],
                "right_context": right_context,
                "received_at": received_at,
                "value": {
                    "document_key": document_id,
                    "relation_id": f"relation:p4-{relation_slug}",
                    "relation_type": relation_type,
                    "from_clause_key": clause_keys[0],
                    "to_clause_key": clause_keys[1],
                    "term_key": "management_fee_rate",
                    "investor_scope": [f"investor:p4-{context}"],
                    "vehicle_scope": [f"vehicle:p4-{context}"],
                    "effective_from": received_at,
                    "effective_to": None,
                    "review_state": "reviewed",
                },
            }
        )
    for context, (dataset_id, _) in P4_SCENARIO_DATASETS.items():
        entity_id = P4_POSITIVE_ENTITY_RECORDS[context][0]
        calculation_key = f"calculation-policy:{context}"
        rounding_key = f"rounding-policy:{context}"
        specs.extend(
            (
                {
                    "dataset_id": dataset_id,
                    "source_record_key": calculation_key,
                    "source_entity_type": "policy",
                    "projection_kind": "calculation_policy",
                    "classification": "authored-contract-evidence",
                    "canonical_entity_id": entity_id,
                    "right_context": context,
                    "value": {
                        "policy_id": f"policy:p4-calculation-{context}",
                        "policy_family": "calculation",
                        "engine": "p4-verified-terms",
                        "calculation_precision": "full-decimal",
                        "ordered_event_kinds": ["source", "calculation", "settlement"],
                        "rounding_policy_projection_key": rounding_key,
                        "effective_from": "2024-01-01",
                        "effective_to": None,
                    },
                },
                {
                    "dataset_id": dataset_id,
                    "source_record_key": rounding_key,
                    "source_entity_type": "policy",
                    "projection_kind": "rounding_policy",
                    "classification": "authored-contract-evidence",
                    "canonical_entity_id": entity_id,
                    "right_context": context,
                    "value": {
                        "policy_id": f"policy:p4-rounding-{context}",
                        "policy_family": "rounding",
                        "minor_unit": ".01",
                        "mode": "half-even",
                        "stage": "final-settlement",
                    },
                },
            )
        )
        scenario_ids = P4_SCENARIO_CONTEXTS[context]
        if {"p4-p18", "p4-p33"} & set(scenario_ids):
            specs.append(
                {
                    "dataset_id": dataset_id,
                    "source_record_key": f"materiality-policy:{context}",
                    "source_entity_type": "policy",
                    "projection_kind": "materiality_policy",
                    "classification": "authored-contract-evidence",
                    "canonical_entity_id": entity_id,
                    "right_context": context,
                    "value": {
                        "policy_id": f"policy:p4-materiality-{context}",
                        "policy_family": "materiality",
                        "absolute_threshold": "5",
                        "equality_is_outside": True,
                    },
                }
            )
        for scenario_id in ("p4-p18", "p4-p33"):
            if scenario_id in scenario_ids:
                specs.append(
                    {
                        "dataset_id": dataset_id,
                        "source_record_key": f"materiality-basis:{scenario_id}:{context}",
                        "source_entity_type": "analysis-case",
                        "projection_kind": "materiality_comparison_basis",
                        "classification": "hypothetical-contract-scenario",
                        "canonical_entity_id": entity_id,
                        "right_context": context,
                        "value": {
                            "basis_id": f"basis:{scenario_id}:{context}",
                            "baseline_scenario_id": f"{scenario_id}-baseline",
                            "counterfactual_scenario_id": f"{scenario_id}-counterfactual",
                            "changed_dimension": "controlled-value",
                        },
                    }
                )
        for scenario_id in scenario_ids:
            dependency_received_at = (
                "2024-04-15"
                if scenario_id == "p4-p29b"
                else "2024-07-15"
                if scenario_id == "p4-p29c"
                else "2024-01-15"
            )
            for record_key, kind, value in _p4_scenario_dependency_specs(
                context, scenario_id
            ):
                specs.append(
                    {
                        "dataset_id": dataset_id,
                        "source_record_key": record_key,
                        "source_entity_type": "analysis-case",
                        "projection_kind": kind,
                        "classification": "hypothetical-contract-scenario",
                        "canonical_entity_id": entity_id,
                        "right_context": context,
                        "received_at": dependency_received_at,
                        "value": value,
                    }
                )
        for scenario_id in scenario_ids:
            inputs, expected_full, expected_settlement = _P4_SCENARIO_CONTROLLED_VALUES[scenario_id]
            received_at = "2024-04-15" if scenario_id == "p4-p29b" else "2024-07-15" if scenario_id == "p4-p29c" else "2024-01-15"
            materiality_key = (
                f"materiality-basis:{scenario_id}:{context}"
                if scenario_id in {"p4-p18", "p4-p33"}
                else None
            )
            specs.append(
                {
                    "dataset_id": dataset_id,
                    "source_record_key": f"scenario:{scenario_id}:{context}",
                    "source_entity_type": "analysis-case",
                    "projection_kind": "scenario_input",
                    "classification": "hypothetical-contract-scenario",
                    "canonical_entity_id": entity_id,
                    "right_context": context,
                    "received_at": received_at,
                    "value": {
                        "scenario_id": scenario_id,
                        "scenario_family": P4_SCENARIO_FAMILY_BY_ID[scenario_id],
                        "controlled_inputs": [inputs],
                        "calculation_policy_projection_key": calculation_key,
                        "materiality_basis_projection_key": materiality_key,
                        "dependency_projection_keys": list(_p4_scenario_dependency_keys(context, scenario_id)),
                        "expected_full_precision": expected_full,
                        "expected_settlement_precision": expected_settlement,
                        "expected_refusal_family": None,
                        "adversarial_source": None,
                    },
                }
            )
        if context in {"shortlisted-nda", "funded-private-partnership"}:
            for scaffold_id, predecessor_id, cutoff_name, received_at in (
                ("scaffold:p4-p29b-from-p29a", "p4-p29a", "early", "2024-04-15"),
                ("scaffold:p4-p29c-from-p29b", "p4-p29b", "amended", "2024-07-15"),
            ):
                request = p4_terms_bundle_request(cutoff_name=cutoff_name, access_context=context)
                specs.append(
                    {
                        "dataset_id": dataset_id,
                        "source_record_key": f"{scaffold_id}:{context}",
                        "source_entity_type": "analysis-case",
                        "projection_kind": "predecessor_request_scaffold",
                        "classification": "hypothetical-contract-scenario",
                        "canonical_entity_id": entity_id,
                        "right_context": context,
                        "received_at": received_at,
                        "value": {
                            "scaffold_id": scaffold_id,
                            "expected_predecessor_scenario_id": predecessor_id,
                            "predecessor_cutoff": normalize_utc(P4_TERMS_CUTOFFS[cutoff_name]),
                            "predecessor_source_dataset_ids": [source.dataset_id for source in request.sources],
                            "predecessor_join_keys": list(request.join_keys),
                            "predecessor_join_policy": request.join_policy,
                            "predecessor_request_json": canonical_bytes(request).decode(),
                            "predecessor_request_digest": sha256(canonical_bytes(request)),
                        },
                    }
                )
    for case_id in P4_AUTHORED_NEGATIVE_CASE_IDS:
        specs.append(
            {
                "dataset_id": P4_NEGATIVE_DATASET[0],
                "source_record_key": case_id,
                "source_entity_type": "analysis-case",
                "projection_kind": "scenario_input",
                "classification": "hypothetical-contract-scenario",
                "canonical_entity_id": P4_NEGATIVE_ENTITY_RECORDS[case_id][0],
                "right_context": P4_NEGATIVE_DATASET[1],
                "received_at": "2024-04-15" if case_id == "p4-l23-future-clause-leak" else "2024-01-15",
                "value": {
                    "scenario_id": case_id,
                    "scenario_family": "negative-adversary",
                    "controlled_inputs": [],
                    "calculation_policy_projection_key": None,
                    "materiality_basis_projection_key": None,
                    "dependency_projection_keys": [],
                    "expected_full_precision": "refuse-before-calculation",
                    "expected_settlement_precision": "refuse-before-settlement",
                    "expected_refusal_family": _P4_NEGATIVE_REFUSAL_FAMILIES[case_id],
                    "adversarial_source": f"isolated-source-row:{case_id}",
                },
            }
        )
    specs.append(
        {
            "dataset_id": P4_METHOD_POLICY_DATASET[0],
            "source_record_key": "policy:p4-method-boundary",
            "source_entity_type": "policy",
            "projection_kind": "method_boundary_policy",
            "classification": "authored-contract-evidence",
            "canonical_entity_id": None,
            "right_context": P4_METHOD_POLICY_DATASET[1],
            "value": {
                "policy_id": "policy:p4-method-boundary",
                "policy_family": "method-boundary",
                "boundary_kind": "verified-hypothetical-only",
                "prohibited_actual_cash_source_classes": ["actual-cash-ledger"],
                "refusal_claim_ids": ["p4b-deferred", "legal-opinion-required"],
                "effective_from": "2024-01-01",
                "effective_to": None,
            },
        }
    )
    return tuple(specs)


def _p4_source_rows(
    right_ids: Mapping[str, str],
) -> tuple[
    tuple[SourceRecordRecord, ...],
    tuple[EvidenceItemRecord, ...],
    tuple[EvidenceSpanRecord, ...],
]:
    default_received_by_dataset = {
        dataset_id: (
            datetime(2024, 7, 15, tzinfo=UTC)
            if dataset_id == "dataset:p4-doc-side-letter"
            else datetime(2024, 4, 15, tzinfo=UTC)
            if dataset_id == "dataset:terms"
            else datetime(2024, 1, 15, tzinfo=UTC)
        )
        for dataset_id in P4_TERMS_DATASETS
    }
    source_rows = []
    item_rows = []
    span_rows = []
    for ordinal, spec in enumerate(_p4_source_specs(), start=1):
        dataset_id = str(spec["dataset_id"])
        projection_kind = str(spec["projection_kind"])
        source_row = with_machine_id(
            "source-record",
            SourceRecordRecord(
                "",
                dataset_id,
                "synthetic-p4-authored",
                str(spec["source_record_key"]),
                str(spec["source_entity_type"]),
            ),
        )
        marker = f"P4-FICTIONAL-SOURCE-{ordinal:03d}"
        source_text = (
            f"Fictional governing-terms evidence {marker} records a controlled "
            "research input and does not describe an actual manager or fund."
        )
        if source_text.count(marker) != 1:
            raise ValueError("P4 source span marker must occur exactly once")
        payload: dict[str, JSONValue] = {
            "record_key": str(spec["source_record_key"]),
            "projection_kind": projection_kind,
            "classification": str(spec["classification"]),
            "source_text": source_text,
            "span_marker": marker,
            "value": spec["value"],
        }
        received = (
            datetime.fromisoformat(str(spec["received_at"])).replace(tzinfo=UTC)
            if "received_at" in spec
            else default_received_by_dataset[dataset_id]
        )
        item_row = with_machine_id(
            "evidence",
            EvidenceItemRecord(
                "",
                right_ids[dataset_id],
                source_row.source_record_id,
                sha256(canonical_bytes(payload)),
                projection_kind.replace("_", "-"),
                f"schema:p4-{projection_kind.replace('_', '-')}-v1",
                "point",
                received,
                None,
                None,
                date(received.year, received.month, received.day),
                None,
                received,
                received,
                None,
                1,
                None,
                "received",
                str(spec["right_context"]),
                "p4-terms-v1",
                "synthetic-research",
                _p4_right_scopes()[dataset_id][1],
                payload,
                canonical_entity_id=(
                    str(spec["canonical_entity_id"])
                    if spec["canonical_entity_id"] is not None
                    else None
                ),
            ),
        )
        start = source_text.index(marker)
        span_row = with_machine_id(
            "span",
            EvidenceSpanRecord(
                "",
                item_row.evidence_item_id,
                "/source_text",
                start,
                start + len(marker),
                sha256(marker.encode()),
            ),
        )
        source_rows.append(source_row)
        item_rows.append(item_row)
        span_rows.append(span_row)
    return tuple(source_rows), tuple(item_rows), tuple(span_rows)


def _p4_version_rows(
    right_ids: Mapping[str, str],
    item_rows: tuple[EvidenceItemRecord, ...],
    span_rows: tuple[EvidenceSpanRecord, ...],
) -> tuple[
    tuple[DatasetVersionRecord, ...],
    tuple[DatasetDeliveryPartitionRecord, ...],
    tuple[DatasetObservationRecord, ...],
    tuple[DatasetObservationPartitionLinkRecord, ...],
]:
    items_by_dataset: dict[str, list[EvidenceItemRecord]] = {
        dataset_id: [] for dataset_id in P4_TERMS_DATASETS
    }
    dataset_by_source_id = {
        item.source_record_id: str(spec["dataset_id"])
        for spec, item in zip(_p4_source_specs(), item_rows, strict=True)
    }
    for item in item_rows:
        dataset_id = dataset_by_source_id[item.source_record_id]
        items_by_dataset[dataset_id].append(item)
    span_by_item = {span.evidence_item_id: span for span in span_rows}

    version_rows = []
    partition_rows = []
    observation_rows = []
    link_rows = []
    for dataset_id in P4_TERMS_DATASETS:
        base_version_id = None
        predecessor_id = None
        materialized: dict[str, dict[str, str]] = {}
        for label in _P4_VERSION_LABELS[dataset_id]:
            is_full = label.endswith("full")
            received = (
                datetime(2024, 7, 15, tzinfo=UTC)
                if "side-letter" in label
                else datetime(2024, 4, 15, tzinfo=UTC)
                if "amendment" in label or "p29b" in label or "future-leak" in label
                else datetime(2024, 7, 15, tzinfo=UTC)
                if "p29c" in label
                else datetime(2024, 1, 15, tzinfo=UTC)
            )
            observed_items = tuple(
                item
                for item in items_by_dataset[dataset_id]
                if item.received_at_utc == received
            )
            observed_rows = [
                {
                    "source_record_id": item.source_record_id,
                    "evidence_item_id": item.evidence_item_id,
                    "observation_status": "present",
                }
                for item in observed_items
            ]
            if is_full:
                materialized = {
                    row["source_record_id"]: row for row in observed_rows
                }
            else:
                materialized.update(
                    {row["source_record_id"]: row for row in observed_rows}
                )
            partition_spec = {
                "partition_key": "all",
                "partition_status": "expected-received",
                "expected_record_count": len(observed_rows),
                "received_record_count": len(observed_rows),
                "received_content_sha256": sha256(
                    canonical_bytes(
                        {
                            "dataset_id": dataset_id,
                            "version_label": label,
                            "evidence_item_ids": [
                                row["evidence_item_id"] for row in observed_rows
                            ],
                        }
                    )
                ),
            }
            version = with_machine_id(
                "dataset-version",
                DatasetVersionRecord(
                    dataset_version_id="",
                    dataset_id=dataset_id,
                    version_label=label,
                    acquisition_right_id=right_ids[dataset_id],
                    published_at=None,
                    first_observed_at_utc=None,
                    received_at_utc=received,
                    embargo_until=None,
                    content_sha256=partition_spec["received_content_sha256"],
                    delivery_mode="full-snapshot" if is_full else "delta",
                    absence_semantics=(
                        "full-snapshot-means-removed" if is_full else "not-inferable"
                    ),
                    completeness_status="complete",
                    expected_partition_manifest_sha256=expected_partition_manifest(
                        (partition_spec,)
                    ),
                    received_partition_manifest_sha256=received_partition_manifest(
                        (partition_spec,)
                    ),
                    expected_partition_count=1,
                    received_partition_count=1,
                    reconstruction_manifest_sha256=reconstruction_manifest(
                        materialized.values()
                    ),
                    reconstruction_row_count=len(materialized),
                    predecessor_dataset_version_id=(
                        None if is_full else predecessor_id
                    ),
                    base_dataset_version_id=None if is_full else base_version_id,
                ),
            )
            if is_full:
                base_version_id = version.dataset_version_id
            predecessor_id = version.dataset_version_id
            manifest_item = items_by_dataset[dataset_id][0]
            manifest_span = span_by_item[manifest_item.evidence_item_id]
            partition = with_machine_id(
                "dataset-partition",
                DatasetDeliveryPartitionRecord(
                    "",
                    version.dataset_version_id,
                    "all",
                    "expected-received",
                    manifest_item.evidence_item_id,
                    manifest_span.evidence_span_id,
                    str(partition_spec["received_content_sha256"]),
                    len(observed_rows),
                    len(observed_rows),
                ),
            )
            version_rows.append(version)
            partition_rows.append(partition)
            for item in observed_items:
                observation = with_machine_id(
                    "dataset-observation",
                    DatasetObservationRecord(
                        "", version.dataset_version_id, item.evidence_item_id, "present"
                    ),
                )
                link = with_machine_id(
                    "dataset-observation-partition",
                    DatasetObservationPartitionLinkRecord(
                        "",
                        observation.dataset_observation_id,
                        partition.dataset_delivery_partition_id,
                    ),
                )
                observation_rows.append(observation)
                link_rows.append(link)
    return (
        tuple(version_rows),
        tuple(partition_rows),
        tuple(observation_rows),
        tuple(link_rows),
    )


def _p4_task3_cases(conn: sqlite3.Connection):
    from ..terms import _persist_p4_term_projections

    positive_bundles = {}
    projection_sets = {}
    for cutoff_name in P4_TERMS_CUTOFFS:
        for access_context in P4_SCENARIO_DATASETS:
            case_id = f"{cutoff_name}:{access_context}"
            bundle = as_known_bundle(
                conn,
                p4_terms_bundle_request(
                    cutoff_name=cutoff_name,
                    access_context=access_context,
                ),
            )
            positive_bundles[case_id] = bundle
            projection_sets[case_id] = _persist_p4_term_projections(conn, bundle)
    negative_bundles = {
        case_id: as_known_bundle(
            conn, p4_terms_negative_bundle_request(case_id=case_id)
        )
        for case_id in P4_AUTHORED_NEGATIVE_CASE_IDS
    }
    method_bundle = as_known_bundle(conn, p4_method_policy_bundle_request())
    projection_sets[P4_METHOD_POLICY_BUNDLE_CASE_ID] = _persist_p4_term_projections(
        conn, method_bundle
    )
    valid_private = p4_terms_bundle_request(
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
    )
    deal_right = _p4_right_id("dataset:p4-doc-deal-by-deal-lpa")
    partial_request = SnapshotBundleRequest(
        decision_at=valid_private.decision_at,
        sources=tuple(
            DatasetSliceRequest(
                dataset_id=source.dataset_id,
                access_context=source.access_context,
                evidence_right_id=(
                    deal_right
                    if source.dataset_id == "dataset:p4-doc-side-letter"
                    else source.evidence_right_id
                ),
                licence_purpose=source.licence_purpose,
                canonical_entity_ids=source.canonical_entity_ids,
                include_unresolved=source.include_unresolved,
                revision_mode=source.revision_mode,
                valid_at=source.valid_at,
                valid_window=source.valid_window,
                require_universe_membership=source.require_universe_membership,
            )
            for source in valid_private.sources
        ),
        join_keys=valid_private.join_keys,
        join_policy=valid_private.join_policy,
    )
    try:
        as_known_bundle(conn, partial_request)
    except EvidenceRefusal as exc:
        if exc.code != "licence-purpose-mismatch":
            raise
    else:
        raise AssertionError("partial P4 document authorization must refuse")
    return (
        positive_bundles,
        negative_bundles,
        method_bundle,
        projection_sets,
        partial_request,
    )


def _p4_manifest(
    conn: sqlite3.Connection,
    positive_bundles,
    negative_bundles,
    method_bundle,
    projection_sets,
    partial_request,
) -> P4TermsFixtureManifest:
    placeholders = ",".join("?" for _ in P4_TERMS_DATASETS)
    entity_records = {
        entity_id: tuple(
            conn.execute(
                "SELECT * FROM canonical_entity WHERE entity_id=?", (entity_id,)
            ).fetchone()
        )
        for entity_id in P4_CANONICAL_ENTITY_IDS
    }
    right_rows = conn.execute(
        f"SELECT * FROM evidence_right WHERE dataset_id IN ({placeholders})",
        P4_TERMS_DATASETS,
    ).fetchall()
    right_ids = {row["dataset_id"]: row["evidence_right_id"] for row in right_rows}
    right_records = {row["dataset_id"]: tuple(row) for row in right_rows}
    version_rows = conn.execute(
        f"SELECT * FROM dataset_version WHERE dataset_id IN ({placeholders})",
        P4_TERMS_DATASETS,
    ).fetchall()
    versions_by_key = {
        (row["dataset_id"], row["version_label"]): row for row in version_rows
    }
    ordered_version_rows = tuple(
        versions_by_key[(dataset_id, label)]
        for dataset_id in P4_TERMS_DATASETS
        for label in _P4_VERSION_LABELS[dataset_id]
    )
    version_ids = tuple(row["dataset_version_id"] for row in ordered_version_rows)
    partition_records = {
        version_id: tuple(
            tuple(row)
            for row in conn.execute(
                "SELECT * FROM dataset_delivery_partition WHERE dataset_version_id=? "
                "ORDER BY dataset_delivery_partition_id",
                (version_id,),
            )
        )
        for version_id in version_ids
    }
    schema_rows = conn.execute(
        "SELECT * FROM payload_schema WHERE payload_schema_id LIKE 'schema:p4-%' "
        "ORDER BY payload_schema_id"
    ).fetchall()
    source_rows = conn.execute(
        f"SELECT * FROM source_record WHERE dataset_id IN ({placeholders}) "
        "ORDER BY source_record_id",
        P4_TERMS_DATASETS,
    ).fetchall()
    item_rows = conn.execute(
        f"SELECT i.*,s.dataset_id AS source_dataset_id FROM evidence_item i "
        "JOIN source_record s USING(source_record_id) "
        f"WHERE s.dataset_id IN ({placeholders}) ORDER BY i.evidence_item_id",
        P4_TERMS_DATASETS,
    ).fetchall()
    item_ids = tuple(row["evidence_item_id"] for row in item_rows)
    item_placeholders = ",".join("?" for _ in item_ids)
    span_rows = conn.execute(
        f"SELECT * FROM evidence_span WHERE evidence_item_id IN ({item_placeholders}) "
        "ORDER BY evidence_span_id",
        item_ids,
    ).fetchall()
    observation_rows = conn.execute(
        f"SELECT o.* FROM dataset_observation o JOIN dataset_version v "
        f"USING(dataset_version_id) WHERE v.dataset_id IN ({placeholders}) "
        "ORDER BY o.dataset_observation_id",
        P4_TERMS_DATASETS,
    ).fetchall()
    source_content = {
        row["evidence_item_id"]: row["content_sha256"] for row in item_rows
    }
    reconstruction = {
        row["dataset_version_id"]: row["reconstruction_manifest_sha256"]
        for row in ordered_version_rows
    }
    bundle_case_records = {}
    for case_id, bundle in positive_bundles.items():
        cutoff_name, access_context = case_id.split(":", 1)
        bundle_case_records[case_id] = P4BundleCaseContract(
            case_id=case_id,
            case_kind="positive",
            cutoff_name=cutoff_name,
            access_context=access_context,
            source_dataset_ids=tuple(
                source.dataset_id for source in bundle.request.sources
            ),
            canonical_entity_ids=(P4_POSITIVE_ENTITY_RECORDS[access_context][0],),
            request_digest=sha256(canonical_bytes(bundle.request)),
            expected_outcome="admitted",
        )
    for case_id, bundle in negative_bundles.items():
        bundle_case_records[case_id] = P4BundleCaseContract(
            case_id=case_id,
            case_kind="negative",
            cutoff_name="side-letter",
            access_context=P4_NEGATIVE_DATASET[1],
            source_dataset_ids=(P4_NEGATIVE_DATASET[0],),
            canonical_entity_ids=(P4_NEGATIVE_ENTITY_RECORDS[case_id][0],),
            request_digest=sha256(canonical_bytes(bundle.request)),
            expected_outcome="bundle-admitted-for-card-refusal",
        )
    bundle_case_records[P4_METHOD_POLICY_BUNDLE_CASE_ID] = P4BundleCaseContract(
        case_id=P4_METHOD_POLICY_BUNDLE_CASE_ID,
        case_kind="method-policy",
        cutoff_name="early",
        access_context="public",
        source_dataset_ids=(P4_METHOD_POLICY_DATASET[0],),
        canonical_entity_ids=(),
        request_digest=sha256(canonical_bytes(method_bundle.request)),
        expected_outcome="admitted",
    )
    adversary_id = P4_TOPOLOGY_ADVERSARY_IDS[0]
    bundle_case_records[adversary_id] = P4BundleCaseContract(
        case_id=adversary_id,
        case_kind="expected-refusal",
        cutoff_name="side-letter",
        access_context="funded-private-partnership",
        source_dataset_ids=tuple(
            source.dataset_id for source in partial_request.sources
        ),
        canonical_entity_ids=(
            P4_POSITIVE_ENTITY_RECORDS["funded-private-partnership"][0],
        ),
        request_digest=sha256(canonical_bytes(partial_request)),
        expected_outcome="licence-purpose-mismatch",
    )
    projections = {
        row.projection_id: row
        for projection_set in projection_sets.values()
        for row in projection_set.rows
    }
    projection_counts = {
        kind: sum(row.projection_kind == kind for row in projections.values())
        for kind in P4_PROJECTION_KINDS
    }
    successful_bundles = {
        **positive_bundles,
        **negative_bundles,
        P4_METHOD_POLICY_BUNDLE_CASE_ID: method_bundle,
    }
    manifest = P4TermsFixtureManifest(
        fixture_id=P4_TERMS_FIXTURE_ID,
        fixture_digest="0" * 64,
        schema_version="evidence-v1",
        schema_digest=schema_digest(conn),
        digest_status=P4_TERMS_DIGEST_STATUS,
        dataset_ids=P4_TERMS_DATASETS,
        document_dataset_ids=tuple(row[0] for row in P4_DOCUMENT_DATASETS.values()),
        scenario_dataset_ids=tuple(row[0] for row in P4_SCENARIO_DATASETS.values()),
        negative_dataset_id=P4_NEGATIVE_DATASET[0],
        method_policy_dataset_id=P4_METHOD_POLICY_DATASET[0],
        canonical_entity_ids=P4_CANONICAL_ENTITY_IDS,
        canonical_entity_records=entity_records,
        document_ids=P4_TERMS_DOCUMENT_IDS,
        right_ids=right_ids,
        right_records=right_records,
        access_contexts={
            dataset_id: _p4_right_scopes()[dataset_id][0]
            for dataset_id in P4_TERMS_DATASETS
        },
        licence_purposes={
            dataset_id: _p4_right_scopes()[dataset_id][1]
            for dataset_id in P4_TERMS_DATASETS
        },
        cutoff_values={
            name: normalize_utc(value) for name, value in P4_TERMS_CUTOFFS.items()
        },
        version_ids=version_ids,
        version_records={row["dataset_version_id"]: tuple(row) for row in ordered_version_rows},
        partition_records=partition_records,
        payload_schema_ids=tuple(row["payload_schema_id"] for row in schema_rows),
        payload_schema_digests={
            row["payload_schema_id"]: row["schema_sha256"] for row in schema_rows
        },
        source_record_ids=tuple(row["source_record_id"] for row in source_rows),
        evidence_item_ids=item_ids,
        evidence_span_ids=tuple(row["evidence_span_id"] for row in span_rows),
        observation_ids=tuple(
            row["dataset_observation_id"] for row in observation_rows
        ),
        source_content_digests=source_content,
        reconstruction_digests=reconstruction,
        projection_ids=tuple(sorted(projections)),
        projection_counts=projection_counts,
        projection_receipt_ids={
            projection_id: row.projection_receipt_id
            for projection_id, row in projections.items()
        },
        positive_case_ids=P4_POSITIVE_CASE_IDS,
        scenario_ids=P4_POSITIVE_SCENARIO_IDS,
        scenario_family_by_id=P4_SCENARIO_FAMILY_BY_ID,
        negative_case_ids=P4_AUTHORED_NEGATIVE_CASE_IDS,
        topology_adversary_ids=P4_TOPOLOGY_ADVERSARY_IDS,
        predecessor_scaffold_ids=P4_PREDECESSOR_SCAFFOLD_IDS,
        bundle_case_records=bundle_case_records,
        slice_receipt_ids={
            f"{case_id}:{slice_.request.dataset_id}": slice_.receipt_id
            for case_id, bundle in successful_bundles.items()
            for slice_ in bundle.slices
        },
        slice_digests={
            f"{case_id}:{slice_.request.dataset_id}": slice_.digest.rsplit(":", 1)[-1]
            for case_id, bundle in successful_bundles.items()
            for slice_ in bundle.slices
        },
        join_receipt_ids={
            case_id: bundle.join_receipt_id
            for case_id, bundle in successful_bundles.items()
        },
        positive_bundle_digests={
            case_id: bundle.bundle_digest.rsplit(":", 1)[-1]
            for case_id, bundle in positive_bundles.items()
        },
        negative_bundle_results={
            **{
                case_id: (
                    "bundle-admitted-for-card-refusal",
                    bundle.bundle_digest,
                )
                for case_id, bundle in negative_bundles.items()
            },
            adversary_id: (
                "licence-purpose-mismatch",
                sha256(canonical_bytes(partial_request)),
            ),
        },
        method_policy_bundle_digest=method_bundle.bundle_digest.rsplit(":", 1)[-1],
        pit_cases={
            f"{dataset_id}:{label}": normalize_utc(
                datetime(2024, 7, 15, tzinfo=UTC)
                if "side-letter" in label or "p29c" in label
                else datetime(2024, 4, 15, tzinfo=UTC)
                if "amendment" in label or "p29b" in label or "future-leak" in label
                else datetime(2024, 1, 15, tzinfo=UTC)
            )
            for dataset_id, labels in _P4_VERSION_LABELS.items()
            for label in labels
        },
        limitations=(
            "Task 2 source closure is provisional until scenario inventory and receipts are authored.",
            "All source sentences and entities are fictional synthetic evidence.",
        ),
        current_attestation="D",
        live_attestation_ceiling="B",
        disclosure="Synthetic authored evidence only; no real manager or fund names.",
    )
    return replace(manifest, fixture_digest=p4_terms_manifest_digest(manifest))


def build_terms_fixture(conn: sqlite3.Connection) -> P4TermsFixtureManifest:
    """Build the idempotent P4 source closure without bundle or projection receipts."""

    from .core import build_core_fixture, core_right_id

    build_core_fixture(conn)
    ingest_entities(
        conn,
        [
            EntityRecord(entity_id, entity_type, label)
            for entity_id, entity_type, label in (
                *P4_POSITIVE_ENTITY_RECORDS.values(),
                *P4_NEGATIVE_ENTITY_RECORDS.values(),
            )
        ],
    )
    scopes = _p4_right_scopes()
    ingest_datasets(
        conn,
        [
            DatasetRecord(
                dataset_id,
                dataset_id.removeprefix("dataset:").replace("-", " ").title(),
                "synthetic-p4-authored",
                "licensed-receipt",
                "p4-terms-v1",
                "synthetic-research",
                scopes[dataset_id][1],
            )
            for dataset_id in P4_TERMS_DATASETS
            if dataset_id != "dataset:terms"
        ],
    )
    jan1 = datetime(2024, 1, 1, tzinfo=UTC)
    right_rows = [
        with_machine_id(
            "right",
            EvidenceRightRecord(
                "",
                f"right-series:{dataset_id.removeprefix('dataset:')}",
                1,
                dataset_id,
                scopes[dataset_id][0],
                scopes[dataset_id][1],
                "active",
                "retain-after-expiry",
                jan1,
                jan1,
                None,
            ),
        )
        for dataset_id in P4_TERMS_DATASETS
        if dataset_id != "dataset:terms"
    ]
    ingest_rights(conn, right_rows)
    right_ids = {row.dataset_id: row.evidence_right_id for row in right_rows}
    right_ids["dataset:terms"] = core_right_id("terms")
    ingest_payload_schemas(conn, _p4_schema_rows())
    source_rows, item_rows, span_rows = _p4_source_rows(right_ids)
    ingest_source_records(conn, source_rows)
    ingest_items(conn, item_rows)
    ingest_spans(conn, span_rows)
    version_rows, partition_rows, observation_rows, link_rows = _p4_version_rows(
        right_ids, item_rows, span_rows
    )
    ingest_dataset_versions(conn, version_rows)
    ingest_dataset_delivery_partitions(conn, partition_rows)
    ingest_dataset_observations(conn, observation_rows)
    ingest_dataset_observation_partition_links(conn, link_rows)
    return _p4_manifest(conn, *_p4_task3_cases(conn))


def p4_terms_bundle_request(
    *, cutoff_name: str, access_context: P4AccessContext
) -> SnapshotBundleRequest:
    entity_id = P4_POSITIVE_ENTITY_RECORDS.get(access_context, (None,))[0]
    if entity_id is None:
        raise EvidenceRefusal("p4-term-bundle-request-invalid")
    request = SnapshotBundleRequest(
        decision_at=P4_TERMS_CUTOFFS.get(cutoff_name, datetime.min.replace(tzinfo=UTC)),
        sources=tuple(
            _p4_slice_request(
                dataset_id,
                canonical_entity_ids=(entity_id,),
                include_unresolved=False,
            )
            for dataset_id in _p4_positive_dataset_ids(
                cutoff_name=cutoff_name, access_context=access_context
            )
        ),
        join_keys=("canonical_entity_id",),
        join_policy="exact-inner-v1",
    )
    validate_p4_positive_bundle_request(request)
    return request


def build_p4_terms_bundle(
    conn: sqlite3.Connection, *, cutoff_name: str, access_context: P4AccessContext
) -> SnapshotBundle:
    from ..terms import _persist_p4_term_projections

    build_terms_fixture(conn)
    request = p4_terms_bundle_request(
        cutoff_name=cutoff_name, access_context=access_context
    )
    bundle = as_known_bundle(conn, request)
    _persist_p4_term_projections(conn, bundle)
    return bundle


def p4_terms_negative_bundle_request(*, case_id: str) -> SnapshotBundleRequest:
    if case_id not in P4_AUTHORED_NEGATIVE_CASE_IDS:
        raise EvidenceRefusal("p4-term-bundle-request-invalid")
    return SnapshotBundleRequest(
        decision_at=P4_TERMS_CUTOFFS["side-letter"],
        sources=(
            _p4_slice_request(
                P4_NEGATIVE_DATASET[0],
                canonical_entity_ids=(P4_NEGATIVE_ENTITY_RECORDS[case_id][0],),
                include_unresolved=False,
            ),
        ),
        join_keys=("canonical_entity_id",),
        join_policy="exact-inner-v1",
    )


def p4_method_policy_bundle_request() -> SnapshotBundleRequest:
    return SnapshotBundleRequest(
        decision_at=P4_TERMS_CUTOFFS["early"],
        sources=(
            _p4_slice_request(
                P4_METHOD_POLICY_DATASET[0],
                canonical_entity_ids=(),
                include_unresolved=True,
            ),
        ),
        join_keys=("canonical_entity_id",),
        join_policy="exact-inner-v1",
    )


def build_p4_method_policy_bundle(conn: sqlite3.Connection) -> SnapshotBundle:
    from ..terms import _persist_p4_term_projections

    build_terms_fixture(conn)
    bundle = as_known_bundle(conn, p4_method_policy_bundle_request())
    _persist_p4_term_projections(conn, bundle)
    return bundle


def p4_terms_manifest_payload(manifest: P4TermsFixtureManifest) -> Mapping[str, JSONValue]:
    return MappingProxyType(
        {
            field.name: getattr(manifest, field.name)
            for field in fields(manifest)
            if field.name != "fixture_digest"
        }
    )


def p4_terms_manifest_digest(manifest: P4TermsFixtureManifest) -> str:
    return sha256(canonical_bytes(p4_terms_manifest_payload(manifest)))


def _p4_rows(
    conn: sqlite3.Connection,
    table: str,
    where: str,
    parameters: tuple[object, ...],
    order_by: str,
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        tuple(row)
        for row in conn.execute(
            f"SELECT * FROM {table} WHERE {where} ORDER BY {order_by}", parameters
        )
    )


@lru_cache(maxsize=1)
def _p4_authoritative_snapshot_and_bundle_ids(
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    from ..schema import connect, initialize

    authored = connect()
    initialize(authored)
    manifest = build_terms_fixture(authored)
    authored.close()
    snapshot_ids = tuple(
        sorted(f"snapshot:sha256:{digest}" for digest in manifest.slice_digests.values())
    )
    bundle_ids = tuple(
        sorted(
            {
                *(
                    f"bundle:sha256:{digest}"
                    for digest in manifest.positive_bundle_digests.values()
                ),
                *(result[1] for result in manifest.negative_bundle_results.values() if result[1].startswith("bundle:")),
                f"bundle:sha256:{manifest.method_policy_bundle_digest}",
            }
        )
    )
    return snapshot_ids, bundle_ids


def p4_terms_authored_closure_payload(conn: sqlite3.Connection) -> Mapping[str, JSONValue]:
    dataset_marks = ",".join("?" for _ in P4_TERMS_DATASETS)
    entity_marks = ",".join("?" for _ in P4_CANONICAL_ENTITY_IDS)
    item_ids = tuple(
        row[0]
        for row in conn.execute(
            "SELECT i.evidence_item_id FROM evidence_item i JOIN source_record s "
            f"USING(source_record_id) WHERE s.dataset_id IN ({dataset_marks}) "
            "ORDER BY i.evidence_item_id",
            P4_TERMS_DATASETS,
        )
    )
    version_ids = tuple(
        row[0]
        for row in conn.execute(
            f"SELECT dataset_version_id FROM dataset_version WHERE dataset_id IN ({dataset_marks}) "
            "ORDER BY dataset_version_id",
            P4_TERMS_DATASETS,
        )
    )
    observation_ids = tuple(
        row[0]
        for row in conn.execute(
            f"SELECT dataset_observation_id FROM dataset_observation WHERE dataset_version_id IN "
            f"({','.join('?' for _ in version_ids)}) ORDER BY dataset_observation_id",
            version_ids,
        )
    )
    snapshot_ids, bundle_ids = _p4_authoritative_snapshot_and_bundle_ids()
    snapshot_marks = ",".join("?" for _ in snapshot_ids)
    snapshot_rows = _p4_rows(
        conn,
        "snapshot_manifest",
        f"snapshot_digest IN ({snapshot_marks})",
        snapshot_ids,
        "snapshot_digest",
    )
    bundle_marks = ",".join("?" for _ in bundle_ids)
    bundle_rows = _p4_rows(
        conn,
        "snapshot_bundle_manifest",
        f"bundle_digest IN ({bundle_marks})",
        bundle_ids,
        "bundle_digest",
    )
    receipt_ids = {
        row[0]
        for row in conn.execute(
            "SELECT receipt_id FROM reconstruction_receipt WHERE claim_id='claim:p4-term-projection'"
        )
    }
    receipt_ids.update(row[4] for row in bundle_rows)
    if snapshot_ids:
        receipt_ids.update(
            row[0]
            for row in conn.execute(
                "SELECT DISTINCT receipt_id FROM receipt_reference WHERE snapshot_digest IN "
                f"({','.join('?' for _ in snapshot_ids)})",
                snapshot_ids,
            )
        )
    receipt_ids_tuple = tuple(sorted(receipt_ids))
    receipt_marks = ",".join("?" for _ in receipt_ids_tuple)
    item_marks = ",".join("?" for _ in item_ids)
    version_marks = ",".join("?" for _ in version_ids)
    observation_marks = ",".join("?" for _ in observation_ids)
    rows: dict[str, JSONValue] = {
        "canonical_entity": _p4_rows(conn, "canonical_entity", f"entity_id IN ({entity_marks})", P4_CANONICAL_ENTITY_IDS, "entity_id"),
        "dataset": _p4_rows(conn, "dataset", f"dataset_id IN ({dataset_marks})", P4_TERMS_DATASETS, "dataset_id"),
        "evidence_right": _p4_rows(conn, "evidence_right", f"dataset_id IN ({dataset_marks})", P4_TERMS_DATASETS, "evidence_right_id"),
        "payload_schema": _p4_rows(conn, "payload_schema", "payload_schema_id LIKE 'schema:p4-%'", (), "payload_schema_id"),
        "source_record": _p4_rows(conn, "source_record", f"dataset_id IN ({dataset_marks})", P4_TERMS_DATASETS, "source_record_id"),
        "evidence_item": _p4_rows(conn, "evidence_item", f"evidence_item_id IN ({item_marks})", item_ids, "evidence_item_id"),
        "evidence_span": _p4_rows(conn, "evidence_span", f"evidence_item_id IN ({item_marks})", item_ids, "evidence_span_id"),
        "dataset_version": _p4_rows(conn, "dataset_version", f"dataset_version_id IN ({version_marks})", version_ids, "dataset_version_id"),
        "dataset_delivery_partition": _p4_rows(conn, "dataset_delivery_partition", f"dataset_version_id IN ({version_marks})", version_ids, "dataset_delivery_partition_id"),
        "dataset_observation": _p4_rows(conn, "dataset_observation", f"dataset_observation_id IN ({observation_marks})", observation_ids, "dataset_observation_id"),
        "dataset_observation_partition_link": _p4_rows(conn, "dataset_observation_partition_link", f"dataset_observation_id IN ({observation_marks})", observation_ids, "dataset_observation_partition_link_id"),
        "snapshot_manifest": snapshot_rows,
        "snapshot_bundle_manifest": bundle_rows,
        "reconstruction_receipt": _p4_rows(conn, "reconstruction_receipt", f"receipt_id IN ({receipt_marks})", receipt_ids_tuple, "receipt_id"),
        "receipt_reference": _p4_rows(conn, "receipt_reference", f"receipt_id IN ({receipt_marks})", receipt_ids_tuple, "receipt_id,ordinal"),
        "receipt_seal": _p4_rows(conn, "receipt_seal", f"receipt_id IN ({receipt_marks})", receipt_ids_tuple, "receipt_id"),
    }
    return MappingProxyType(rows)


def p4_terms_authored_closure_digest(conn: sqlite3.Connection) -> str:
    return sha256(canonical_bytes(p4_terms_authored_closure_payload(conn)))


def verify_p4_terms_manifest(
    conn: sqlite3.Connection, manifest: P4TermsFixtureManifest
) -> bool:
    return not _p4_manifest_verification_failures(conn, manifest)


def _p4_manifest_verification_failures(
    conn: sqlite3.Connection, manifest: P4TermsFixtureManifest
) -> tuple[str, ...]:
    from ..schema import connect, initialize

    if manifest.fixture_digest != p4_terms_manifest_digest(manifest):
        return ("manifest-digest-mismatch",)
    authored = connect()
    initialize(authored)
    expected = build_terms_fixture(authored)
    failures = []
    comparable = manifest
    if manifest.digest_status != expected.digest_status:
        comparable = replace(
            manifest,
            digest_status=expected.digest_status,
            fixture_digest="0" * 64,
        )
        comparable = replace(
            comparable, fixture_digest=p4_terms_manifest_digest(comparable)
        )
    if comparable != expected:
        failures.append("manifest-contract-mismatch")
    if p4_terms_authored_closure_digest(conn) != p4_terms_authored_closure_digest(authored):
        failures.append("authored-closure-mismatch")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        failures.append("foreign-key-check-failed")
    authored.close()
    if failures:
        return tuple(failures)
    if manifest.digest_status == "provisional-unreviewed":
        return ("digest-status-provisional-unreviewed",)
    if None in {
        P4_TERMS_AUTHORED_SCHEMA_SHA256,
        P4_TERMS_AUTHORED_CLOSURE_SHA256,
        P4_TERMS_AUTHORED_MANIFEST_SHA256,
    }:
        return ("reviewed-digests-unpinned",)
    reviewed_failures = []
    if manifest.schema_digest != P4_TERMS_AUTHORED_SCHEMA_SHA256:
        reviewed_failures.append("reviewed-schema-digest-mismatch")
    if p4_terms_authored_closure_digest(conn) != P4_TERMS_AUTHORED_CLOSURE_SHA256:
        reviewed_failures.append("reviewed-closure-digest-mismatch")
    if manifest.fixture_digest != P4_TERMS_AUTHORED_MANIFEST_SHA256:
        reviewed_failures.append("reviewed-manifest-digest-mismatch")
    return tuple(reviewed_failures)


def build_s7_terms_sources(conn, *, death_observation_id: str | None = None):
    """Author S7 basis, relationship, optional death, and method-policy evidence."""

    from datetime import UTC, datetime

    from ..model import DatasetSliceRequest, SnapshotBundleRequest
    from ..snapshot import as_known_bundle
    from .s7 import (
        S7_CUTOFFS,
        S7_RELATIONSHIP_FIELDS,
        S7MethodPolicyEvidence,
        _ingest_s7_dataset,
        s7_provisional_relationship_items,
    )

    early = datetime(2024, 3, 1, tzinfo=UTC)
    latest = datetime(2024, 9, 1, tzinfo=UTC)
    basis_fields = (
        "term_id",
        "source_product_key",
        "effective_from",
        "effective_to",
        "term_kind",
        "value",
        "unit",
        "scope",
    )
    relationship_fields = S7_RELATIONSHIP_FIELDS
    death_fields = (
        "finding_type",
        "source_record_key",
        "canonical_product_id",
        "effective_at",
        "first_known_at",
        "affected_observation_ids",
        "reason_code",
    )
    relationship_specs = (
        (
            "s7-hf-overlap-path-offers",
            "offers",
            "manager:x3-00",
            "strategy:x3-01",
            "2024-02-01T00:00:00Z",
            "2024-03-01T00:00:00Z",
            "The reviewed hedge overlap path offers strategy x3-01 during February.",
            "s7-l9-overlap-path",
        ),
        (
            "s7-hf-overlap-owner-a",
            "reported_through",
            "strategy:x3-00",
            "composite:x3-01",
            "2024-02-01T00:00:00Z",
            "2024-03-01T00:00:00Z",
            "Ownership path A reports the overlap composite through strategy x3-00.",
            "s7-l9-overlap-owner",
        ),
        (
            "s7-hf-overlap-owner-b",
            "reported_through",
            "strategy:x3-01",
            "composite:x3-01",
            "2024-02-01T00:00:00Z",
            "2024-03-01T00:00:00Z",
            "Ownership path B reports the overlap composite through strategy x3-01.",
            "s7-l9-overlap-owner",
        ),
        ("lead-predecessor-employment", "employed_by", "person:s7-lead", "manager:x3-01", "2020-01-01T00:00:00Z", "2024-01-01T00:00:00Z", "The lead was employed by the predecessor through 2023-12.", "employment"),
        ("lead-current-employment", "employed_by", "person:s7-lead", "manager:x3-00", "2024-01-01T00:00:00Z", "", "The lead joined the current manager at the segment boundary.", "employment"),
        ("support-predecessor-employment", "employed_by", "person:s7-support", "manager:x3-01", "2020-01-01T00:00:00Z", "", "The support lead remained with the predecessor.", "employment"),
        ("predecessor-claim", "predecessor_claim", "manager:x3-01", "manager:x3-00", "2024-01-01T00:00:00Z", "", "The current manager names the prior manager as predecessor.", "identity-claim"),
        ("support-transfer-scope", "transfer_scope", "person:s7-support", "strategy:x3-04", "2023-01-01T00:00:00Z", "", "The sourced scope covers strategy x3-04.", "strategy:x3-04"),
        ("support-transfer-contradiction", "contradicts_transfer", "person:s7-support", "strategy:x3-05", "2024-06-01T00:00:00Z", "", "The source contradicts transfer for strategy x3-05.", "strategy:x3-05"),
    )
    items = [
        {
            "source_key": "s7-hf-fee-basis",
            "record_kind": "s7-basis-term",
            "payload": dict(
                zip(
                    basis_fields,
                    ("fee-basis-v1", "s7-hf-main", "2024-01-01T00:00:00Z", "", "fee-basis", "net-of-management-and-incentive-fees", "declaration", "composite"),
                    strict=True,
                )
            ),
            "available_at": early,
            "effective_from": early,
            "temporal_type": "interval",
            "source_entity_type": "term",
        }
    ]
    for key, relation, source, target, start, end, assertion, scope in relationship_specs:
        point = relation in {"predecessor_claim", "contradicts_transfer"}
        items.append(
            {
                "source_key": key,
                "record_kind": "s7-relationship-evidence",
                "payload": dict(
                    zip(
                        relationship_fields,
                        (key, relation, source, target, start, end, assertion, scope),
                        strict=True,
                    )
                ),
                "available_at": early,
                "effective_at": (
                    datetime.fromisoformat(start.replace("Z", "+00:00")) if point else None
                ),
                "effective_from": (
                    None if point else datetime.fromisoformat(start.replace("Z", "+00:00"))
                ),
                "effective_to": (
                    datetime.fromisoformat(end.replace("Z", "+00:00")) if end and not point else None
                ),
                "temporal_type": "point" if point else "interval",
                "source_entity_type": "relationship",
            }
        )
    provisional_relationship_items = s7_provisional_relationship_items("hedge-fund", early)
    items.extend(provisional_relationship_items)
    early_observations = tuple((str(item["source_key"]), 1, "present", None) for item in items)
    versions = [
        {
            "version_label": "early",
            "available_at": early,
            "delivery_mode": "full-snapshot",
            "absence_semantics": "not-inferable",
            "observations": early_observations,
        }
    ]
    if death_observation_id is not None:
        affected = conn.execute(
            "SELECT m.canonical_entity_id,i.effective_at FROM entity_mapping m "
            "JOIN evidence_item i ON i.evidence_item_id=m.source_evidence_item_id "
            "WHERE m.dataset_observation_id=? AND m.mapping_status='resolved'",
            (death_observation_id,),
        ).fetchall()
        if len(affected) != 1 or affected[0]["canonical_entity_id"] is None:
            raise ValueError("s7-death-observation-mapping-mismatch")
        canonical_product_id = affected[0]["canonical_entity_id"]
        effective_at = affected[0]["effective_at"]
        items.append(
            {
                "source_key": "s7-hf-death-evidence",
                "record_kind": "s7-death-evidence",
                "payload": dict(
                    zip(
                        death_fields,
                        (
                            "later-dead-product",
                            "s7-hf-closed:2023-12",
                            canonical_product_id,
                            effective_at,
                            "2024-09-01T00:00:00Z",
                            death_observation_id,
                            "later-dead-product",
                        ),
                        strict=True,
                    )
                ),
                "available_at": latest,
                "effective_at": datetime.fromisoformat(effective_at.replace("Z", "+00:00")),
                "source_entity_type": "death-evidence",
            }
        )
        versions.append(
            {
                "version_label": "latest",
                "available_at": latest,
                "delivery_mode": "delta",
                "absence_semantics": "explicit-tombstone-only",
                "observations": (
                    ("s7-hf-death-evidence", 1, "present", None),
                    *(
                        (
                            row["source_key"],
                            1,
                            "explicitly-removed",
                            "superseded-by-x3-reviewed-lineage",
                        )
                        for row in provisional_relationship_items
                    ),
                ),
            }
        )
    _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-lineage-terms",
        label="S7 lineage and basis terms",
        source_system="authored-s7",
        availability_policy="manager-receipt",
        access_context="shortlisted-nda",
        licence_purpose="s7-research",
        schemas=(
            ("schema:s7-basis-term-v1", "s7-basis-term", basis_fields),
            ("schema:s7-relationship-evidence-v1", "s7-relationship-evidence", relationship_fields),
            ("schema:s7-death-evidence-v1", "s7-death-evidence", death_fields),
        ),
        items=items,
        versions=versions,
    )

    policy_fields = ("policy_id", "output_pointer", "statement", "prohibited_outputs")
    policy_payload = {
        "policy_id": "s7-method-boundary/v1",
        "output_pointer": "/refusals/performance-estimator",
        "statement": (
            "S7 reconstructs lineage and basis-qualified panels; it does not estimate "
            "alpha, Sharpe, IRR, PME, skill, or manager ranking."
        ),
        "prohibited_outputs": "alpha|sharpe|irr|pme|skill|manager-ranking",
    }
    policy_rows = _ingest_s7_dataset(
        conn,
        dataset_id="dataset:s7-method-boundary",
        label="S7 method boundary",
        source_system="authored-s7",
        availability_policy="public-publication",
        access_context="public",
        licence_purpose="s7-research",
        schemas=(("schema:s7-method-policy-v1", "s7-method-policy", policy_fields),),
        items=(
            {
                "source_key": "s7-method-boundary-v1",
                "record_kind": "s7-method-policy",
                "payload": policy_payload,
                "available_at": early,
                "effective_from": datetime(2024, 1, 1, tzinfo=UTC),
                "temporal_type": "interval",
                "source_entity_type": "policy",
            },
        ),
        versions=(
            {
                "version_label": "v1",
                "available_at": early,
                "delivery_mode": "full-snapshot",
                "absence_semantics": "not-inferable",
                "observations": (("s7-method-boundary-v1", 1, "present", None),),
            },
        ),
    )
    policy_item = next(item for item in policy_rows["items"] if item.record_kind == "s7-method-policy")
    policy_span = next(
        span for span in policy_rows["spans"]
        if span.evidence_item_id == policy_item.evidence_item_id and span.json_pointer == "/statement"
    )
    policy_observation = next(
        row for row in policy_rows["observations"] if row.evidence_item_id == policy_item.evidence_item_id
    )
    policy_version = policy_rows["versions"][0]
    request = DatasetSliceRequest(
        "dataset:s7-method-boundary",
        "public",
        policy_rows["right_id"],
        "s7-research",
        revision_mode="latest-known",
        include_unresolved=True,
    )
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS["latest"],
            (request,),
            ("evidence_item_id",),
            "s7-method-policy-v1",
        ),
    )
    schema = next(row for row in policy_rows["schemas"] if row.payload_schema_id == "schema:s7-method-policy-v1")
    policy = S7MethodPolicyEvidence(
        "s7-method-boundary/v1",
        "dataset:s7-method-boundary",
        schema.payload_schema_id,
        schema.schema_sha256,
        policy_item.evidence_item_id,
        policy_span.evidence_span_id,
        policy_observation.dataset_observation_id,
        policy_version.dataset_version_id,
        policy_rows["right_id"],
        bundle.slices[0].digest,
        bundle.slices[0].receipt_id,
        bundle.bundle_digest,
        bundle.join_receipt_id,
        policy_item.content_sha256,
    )
    return policy, bundle


def build_s7_death_bundle(conn):
    """Materialize the separately receipted latest-known S7 death-evidence path."""

    from ..lineage import make_receipt, store_receipt, verify_receipt
    from ..model import DatasetSliceRequest, ReceiptReference, SnapshotBundleRequest
    from ..snapshot import as_known_bundle
    from .s7 import S7_CUTOFFS

    right_id = conn.execute(
        "SELECT evidence_right_id FROM evidence_right "
        "WHERE dataset_id='dataset:s7-lineage-terms' AND access_context='shortlisted-nda'"
    ).fetchone()[0]
    bundle = as_known_bundle(
        conn,
        SnapshotBundleRequest(
            S7_CUTOFFS["latest"],
            (
                DatasetSliceRequest(
                    "dataset:s7-lineage-terms",
                    "shortlisted-nda",
                    right_id,
                    "s7-research",
                    revision_mode="latest-known",
                    include_unresolved=True,
                ),
            ),
            ("evidence_item_id",),
            "s7-death-evidence-v1",
        ),
    )
    if not any(row["payload"].get("reason_code") == "later-dead-product" for row in bundle.slices[0].rows):
        raise ValueError("s7-death-evidence-missing")
    death = conn.execute(
        "SELECT i.evidence_item_id,sp.evidence_span_id,i.payload_json "
        "FROM evidence_item i JOIN evidence_span sp USING(evidence_item_id) "
        "WHERE i.record_kind='s7-death-evidence' AND sp.json_pointer='/reason_code'"
    ).fetchall()
    if len(death) != 1:
        raise ValueError("s7-death-evidence-missing")
    item_id, span_id, payload_json = death[0]
    receipt = make_receipt(
        claim_id="claim:s7-death-evidence",
        output_locator="/death-evidence",
        input_digest=bundle.bundle_digest,
        output_schema_id="schema:s7-death-evidence-v1",
        current_attestation="D",
        live_attestation_ceiling="B",
        algorithm_id="s7-death-span-v1",
        algorithm_version="1",
        parameters={"json_pointer": "/reason_code"},
        value={"item_id": item_id, "span_id": span_id, "payload": payload_json},
        references=(
            ReceiptReference(
                "/death-evidence",
                "evidence-item",
                item_id,
                "included",
                "",
                "schema:s7-death-evidence-v1",
                "/",
                "input",
            ),
            ReceiptReference(
                "/death-evidence",
                "evidence-span",
                span_id,
                "included",
                "",
                "schema:s7-death-evidence-v1",
                "/reason_code",
                "input",
            ),
        ),
    )
    existing = conn.execute(
        "SELECT 1 FROM reconstruction_receipt WHERE receipt_id=?", (receipt.receipt_id,)
    ).fetchone()
    if existing is None:
        store_receipt(conn, receipt)
    verify_receipt(conn, receipt.receipt_id, bundle)
    return bundle
