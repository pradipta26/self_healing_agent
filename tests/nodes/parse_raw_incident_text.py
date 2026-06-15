import pytest

from self_healing_agent.agent.nodes.parse_raw_incident_text import parse_raw_incident_details


TEST_CASES = [
    (
        "Host Infra",
        "System: UVWX , DC: AWS-W , MetricName: Server CPU % , Application: UVWX-ONE SEARCH-INFRA for host: host.my-domain.com , Instance: host.my-domain.com has Server CPU % >= 99.0",
        {
            "incident_type": "infra_host",
            "service_domain": "UVWX",
            "datacenter": "AWS-W",
            "metric_name": ["Server CPU %"],
            "app_name": "UVWX-ONE SEARCH-INFRA",
            "host": "host.my-domain.com",
            "instances": ["host.my-domain.com"],
            "instance_host": [],
            "reason": "Server CPU % >= 99.0",
            "warnings": [],
        },
    ),
    (
        "Host Infra",
        "System: MNOP , DC: AWS-W , MetricName: jvm mismatch , Application: MNOP-MNOP-JVM-STATUS for host: AWS-W MCS PNO-MNOP JVM Status Mismatch, 6 missing, 2 extra MNOP-BATCH-CASSANDRAREALTIME-PRD-AW2:MNOP-BATCH-CASSANDRAREALTIME-PRD-AW2 = missing, WLS-MNOP-CXPNOB2-AW2:host.my-domain.com:CXP_PNO_B2C:Server1:13001 = missing, WLS-MNOP-CXPNOB2-AW2:host.my-domain.com:CXP_PNO_B2C:Server3:13003 = missing, WLS-MNOP-CXPNOB2-AW2:host.my-domain.com:DVS_PNO_B2C:Server3:13003 = missing, Instance: Reference List: AWS-West.PNO_JVMList has jvm mismatch >= 0.0",
        {
            "incident_type": "infra_host",
            "service_domain": "MNOP",
            "datacenter": "AWS-W",
            "metric_name": ["jvm mismatch"],
            "app_name": "MNOP-MNOP-JVM-STATUS",
            "host": "AWS-W MCS PNO-MNOP",
            "instances": ["Reference List: AWS-West.PNO_JVMList"],
            "instance_host": [],
            "reason": "jvm mismatch >= 0.0",
            "warnings": ["HOST_NOT_FQDN"],
        },
    ),
    (
        "Host Infra",
        "System: YZAB , DC: TDC , MetricName: /log usage , Application: YZAB-SCMDATA-INFRA for host: host.my-domain.com , Instance: host.my-domain.com:/log has /log usage >= 96.0",
        {
            "incident_type": "infra_host",
            "service_domain": "YZAB",
            "datacenter": "TDC",
            "metric_name": ["/log usage"],
            "app_name": "YZAB-SCMDATA-INFRA",
            "host": "host.my-domain.com",
            "instances": ["host.my-domain.com:/log"],
            "instance_host": ["host.my-domain.com"],
            "reason": "/log usage >= 96.0",
            "warnings": [],
        },
    ),
    (
        "Host Infra",
        "System: QRST , DC: SDC , MetricName: /var/adm/WebSphere usage , Application: QRST-DVS-INFRA for host: host.my-domain.com , Instance: host.my-domain.com:/var/adm/WebSphere has /var/adm/WebSphere usage >= 92.0",
        {
            "incident_type": "infra_host",
            "service_domain": "QRST",
            "datacenter": "SDC",
            "metric_name": ["/var/adm/WebSphere usage"],
            "app_name": "QRST-DVS-INFRA",
            "host": "host.my-domain.com",
            "instances": ["host.my-domain.com:/var/adm/WebSphere"],
            "instance_host": ["host.my-domain.com"],
            "reason": "/var/adm/WebSphere usage >= 92.0",
            "warnings": [],
        },
    ),
    (
        "Service DC",
        "Reason: 300% more traffic is observed compared to past window average traffic - 8188.0 System: AAAR, DC: SDC, MetricName: Traffic, Application: AAAR-SAFEGUARD-SSOIGSTREAMPROCESSING",
        {
            "incident_type": "service_dc",
            "service_domain": "AAAR",
            "datacenter": "SDC",
            "metric_name": ["Traffic"],
            "app_name": "AAAR-SAFEGUARD-SSOIGSTREAMPROCESSING",
            "host": None,
            "instances": [],
            "instance_host": [],
            "reason": "300% more traffic is observed compared to past window average traffic - 8188.0",
            "warnings": [],
        },
    ),
    (
        "Service DC",
        "Reason: 1 hosts have alb-502-count >= 7.0, Configured Host Capacity - 0 System: LMNO, DC: AWS-E, MetricName: alb-502-count, Application: LMNO-SOE-Sales-ALB-Logs",
        {
            "incident_type": "service_dc",
            "service_domain": "LMNO",
            "datacenter": "AWS-E",
            "metric_name": ["alb-502-count"],
            "app_name": "LMNO-SOE-Sales-ALB-Logs",
            "host": None,
            "instances": [],
            "instance_host": [],
            "reason": "1 hosts have alb-502-count >= 7.0, Configured Host Capacity - 0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: Active Threads >= 200.0, Avg Response Time(ms) >= 20000.0 System: AAAC, DC: TDC, MetricName: Active Threads, Avg Response Time(ms), Application: AAAC-ACSS-AMQ, Instance: host-01:ACSS-MQ:acsstr-mq1:5701",
        {
            "incident_type": "service_instance",
            "service_domain": "AAAC",
            "datacenter": "TDC",
            "metric_name": ["Active Threads", "Avg Response Time(ms)"],
            "app_name": "AAAC-ACSS-AMQ",
            "host": None,
            "instances": "host-01:ACSS-MQ:acsstr-mq1:5701",
            "instance_host": [],
            "reason": "Active Threads >= 200.0, Avg Response Time(ms) >= 20000.0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: Avg Response Time(ms) >= 17086.0 System: QRST, DC: AWS-W, MetricName: Avg Response Time(ms), Application: QRST-ORBPM-B2B-NOTIFICATION, Instance: host.my-domain.com_NOTIFICATION_9098",
        {
            "incident_type": "service_instance",
            "service_domain": "QRST",
            "datacenter": "AWS-W",
            "metric_name": ["Avg Response Time(ms)"],
            "app_name": "QRST-ORBPM-B2B-NOTIFICATION",
            "host": None,
            "instances": "host.my-domain.com_NOTIFICATION_9098",
            "instance_host": [],
            "reason": "Avg Response Time(ms) >= 17086.0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: 5xx >= 30.0 System: AACV, DC: TDC, MetricName: 5xx, Application: AACV-WORKHUB-NXTGEN-INFRA, Instance: WORKHUB_NXTGEN_LOGS|opt|application|access_log",
        {
            "incident_type": "service_instance",
            "service_domain": "AACV",
            "datacenter": "TDC",
            "metric_name": ["5xx"],
            "app_name": "AACV-WORKHUB-NXTGEN-INFRA",
            "host": None,
            "instances": "WORKHUB_NXTGEN_LOGS|opt|application|access_log",
            "instance_host": [],
            "reason": "5xx >= 30.0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: pegaerrors >= 105000.0 System: WXYZ, DC: AWS-W, MetricName: pegaerrors, Application: WXYZ-RTD-NBX-NEXTGEN, Instance: ERROR: ORA-12541 - Cannot connect. No listener at host db.my-domain.com",
        {
            "incident_type": "service_instance",
            "service_domain": "WXYZ",
            "datacenter": "AWS-W",
            "metric_name": ["pegaerrors"],
            "app_name": "WXYZ-RTD-NBX-NEXTGEN",
            "host": None,
            "instances": "ERROR: ORA-12541 - Cannot connect. No listener at host db.my-domain.com",
            "instance_host": ["db.my-domain.com"],
            "reason": "pegaerrors >= 105000.0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: oracle-db-sp-queue-status >= 3.0 System: ABDC, DC: TDC, MetricName: oracle-db-sp-queue-status, Application: ABDC-ABDC_SPLEX-Common-Operations, Instance: host.my-domain.com:Post:sample_queue:2058",
        {
            "incident_type": "service_instance",
            "service_domain": "ABDC",
            "datacenter": "TDC",
            "metric_name": ["oracle-db-sp-queue-status"],
            "app_name": "ABDC-ABDC_SPLEX-Common-Operations",
            "host": None,
            "instances": "host.my-domain.com:Post:sample_queue:2058",
            "instance_host": [],
            "reason": "oracle-db-sp-queue-status >= 3.0",
            "warnings": [],
        },
    ),
    (
        "Service Instance",
        "Reason: 5xx >= 30.0 System: AACV, DC: TDC, MetricName: 5xx, Application: AACV-WORKHUB-NXTGEN-INFRA, Instance: WORKHUB_NXTGEN_LOGS|opt|application|access_log",
        {
            "incident_type": "service_instance",
            "service_domain": "AACV",
            "datacenter": "TDC",
            "metric_name": ["5xx"],
            "app_name": "AACV-WORKHUB-NXTGEN-INFRA",
            "host": None,
            "instances": "WORKHUB_NXTGEN_LOGS|opt|application|access_log",
            "instance_host": [],
            "reason": "5xx >= 30.0",
            "warnings": [],
        },
    ),
    (
        "System Instance",
        "Reason: CW_ReadIOPS >= 20000.0 System: WXYZ, DC: AWS-E, MetricName: CW_ReadIOPS, Application: WXYZ-WXYZ Databases-OMP, Host: db-host",
        {
            "incident_type": "system_instance",
            "service_domain": "WXYZ",
            "datacenter": "AWS-E",
            "metric_name": ["CW_ReadIOPS"],
            "app_name": "WXYZ-WXYZ Databases-OMP",
            "host": "db-host",
            "instances": [],
            "instance_host": [],
            "reason": "CW_ReadIOPS >= 20000.0",
            "warnings": ["HOST_NOT_FQDN"],
        },
    ),
    (
        "System Instance",
        "Reason: ibmmqdepth_TDCqueues >= 32000.0 System: MNOP, DC: TDC, MetricName: ibmmqdepth_TDCqueues, Application: MNOP-CPF_MQ-IBMMQ, Host: host.my-domain.com",
        {
            "incident_type": "system_instance",
            "service_domain": "MNOP",
            "datacenter": "TDC",
            "metric_name": ["ibmmqdepth_TDCqueues"],
            "app_name": "MNOP-CPF_MQ-IBMMQ",
            "host": "host.my-domain.com",
            "instances": [],
            "instance_host": [],
            "reason": "ibmmqdepth_TDCqueues >= 32000.0",
            "warnings": [],
        },
    ),
    (
        "System DC",
        "Reason: 1 hosts have oracle-db-session-blocker >= 300.0 System: AABE, DC: SDC, MetricName: oracle-db-session-blocker, Application: AABE-EVV-Databases-VIP",
        {
            "incident_type": "system_dc",
            "service_domain": "AABE",
            "datacenter": "SDC",
            "metric_name": ["oracle-db-session-blocker"],
            "app_name": "AABE-EVV-Databases-VIP",
            "host": None,
            "instances": [],
            "instance_host": [],
            "reason": "1 hosts have oracle-db-session-blocker >= 300.0",
            "warnings": [],
        },
    ),
]


@pytest.mark.parametrize(
    ("label", "incident_details", "expected_parsed_incident"),
    TEST_CASES,
)
def test_parse_raw_incident_text_quick_test_main_scenarios(
    label: str,
    incident_details: str,
    expected_parsed_incident: dict,
) -> None:
    result = parse_raw_incident_details({"incident_raw": incident_details})
    structured_input = result["structured_input"]

    assert result["error_flag"] is False, f"unexpected parser error for {label}"
    assert structured_input["service_domain"] == expected_parsed_incident["service_domain"]
    assert structured_input["datacenter"] == expected_parsed_incident["datacenter"].replace("-", "")
    assert structured_input["app_name"] == expected_parsed_incident["app_name"]

# To run test:
# cd self_healing_agent
# uv run --with pytest pytest -q tests/nodes/parse_raw_incident_text.py
