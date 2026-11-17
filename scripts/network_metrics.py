"""Provider-neutral dashboard metrics with compatible provider-specific aliases."""
import prometheus_client


class MirroredGauge:
    def __init__(self, *gauges):
        self.gauges = gauges

    def set(self, value):
        for gauge in self.gauges:
            gauge.set(value)


class NetworkMetrics:
    def __init__(self, prefix, display_name):
        definitions = [
            ('open_ports', 'open_ports_total', 'network_observed_ports', 'Distinct observed port numbers'),
            ('services', 'services_total', 'network_observed_services', 'Observed services'),
            ('enabled', 'monitor_enabled', 'network_monitor_enabled', 'Network integration configured'),
            ('success', 'scrape_success', 'network_lookup_success', 'Last network lookup succeeded'),
            ('last_success', 'last_success_timestamp_seconds', 'network_last_success_timestamp_seconds', 'Last successful network lookup'),
        ]
        for attribute, suffix, generic, description in definitions:
            setattr(self, attribute, MirroredGauge(
                prometheus_client.Gauge(prefix + '_' + suffix, description),
                prometheus_client.Gauge(generic, description)))
        self.provider = prometheus_client.Gauge('network_provider_info', 'Selected network data provider', ['provider'])
        self.provider.labels(display_name).set(1)
