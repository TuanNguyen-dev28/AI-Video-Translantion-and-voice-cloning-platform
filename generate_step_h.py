import os

shared_dir = 'src/AIVideoPlatform.Shared/Observability'
os.makedirs(shared_dir, exist_ok=True)

obs_code = '''using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using OpenTelemetry.Trace;
using OpenTelemetry.Metrics;

namespace AIVideoPlatform.Shared.Observability;

public static class ObservabilityExtensions
{
    public static IServiceCollection AddCustomObservability(this IServiceCollection services, string serviceName)
    {
        services.AddOpenTelemetry()
            .WithTracing(tracerProviderBuilder =>
            {
                tracerProviderBuilder
                    .AddSource(serviceName)
                    .AddAspNetCoreInstrumentation()
                    .AddHttpClientInstrumentation();
            })
            .WithMetrics(metricsProviderBuilder =>
            {
                metricsProviderBuilder
                    .AddMeter(serviceName)
                    .AddAspNetCoreInstrumentation()
                    .AddHttpClientInstrumentation();
            });

        return services;
    }
}
'''
with open(os.path.join(shared_dir, 'ObservabilityExtensions.cs'), 'w', encoding='utf-8') as f: f.write(obs_code)

