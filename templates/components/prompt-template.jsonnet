local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

{

    prompts:: default_prompts,

    "prompt" +: {
    
        create:: function(engine)

            local container =
                engine.container("prompt")
                    .with_image(images.trustgraph)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,

                        "--text-completion-request-queue",
                        "non-persistent://tg/request/text-completion",
                        "--text-completion-response-queue",
                        "non-persistent://tg/response/text-completion-response",

                        "--system-prompt",
                        $["prompts"]["system-template"],

                        "--prompt",

                    ] + [
                        p.key + "=" + p.value.prompt,
                        for p in std.objectKeysValuesAll($.prompts.templates)
                    ] + [
                        "--prompt-response-type"
                    ] + [
                        p.key + "=" + p.value["response-type"],
                        for p in std.objectKeysValuesAll($.prompts.templates)
                        if std.objectHas(p.value, "response-type")
                    ] + [
                        "--prompt-schema"
                    ] + [
                        (
                            p.key + "=" +
                            std.manifestJsonMinified(p.value["schema"])
                        )
                        for p in std.objectKeysValuesAll($.prompts.templates)
                        if std.objectHas(p.value, "schema")
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "prompt", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "prompt-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("prompt-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,
                        "-i",
                        "non-persistent://tg/request/prompt-rag",
                        "-o",
                        "non-persistent://tg/response/prompt-rag-response",
                        "--text-completion-request-queue",
                        "non-persistent://tg/request/text-completion-rag",
                        "--text-completion-response-queue",
                        "non-persistent://tg/response/text-completion-rag-response",

                        "--system-prompt",
                        $["prompts"]["system-template"],

                        "--prompt",

                    ] + [
                        p.key + "=" + p.value.prompt,
                        for p in std.objectKeysValuesAll($.prompts.templates)
                    ] + [
                        "--prompt-response-type"
                    ] + [
                        p.key + "=" + p.value["response-type"],
                        for p in std.objectKeysValuesAll($.prompts.templates)
                        if std.objectHas(p.value, "response-type")
                    ] + [
                        "--prompt-schema"
                    ] + [
                        (
                            p.key + "=" +
                            std.manifestJsonMinified(p.value["schema"])
                        )
                        for p in std.objectKeysValuesAll($.prompts.templates)
                        if std.objectHas(p.value, "schema")
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "prompt-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

} + default_prompts

