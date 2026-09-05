"""
6. Conditions, and the split between valid and invalid.

    python examples/tutorial/06_conditions.py

A sweep generates combinations mechanically, and some of them make no sense --
a decoder wider than the encoder, a batch too large for the accumulation steps.
Conditions let a configuration reject itself.

Resolution then returns two sets rather than raising. Invalid keys are not
errors to fix; they are the combinations a sweep should skip, and each one
carries the reason it was excluded.
"""

from cinnamon.configuration import Configuration, Param
from cinnamon.registry import Registry


class Autoencoder:
    def __init__(self, encoder_width: int, decoder_width: int):
        self.encoder_width = encoder_width
        self.decoder_width = decoder_width


class AutoencoderConfig(Configuration):
    encoder_width: int = Param(128, variants=[64])
    decoder_width: int = Param(64, variants=[128])

    def model_post_init(self, context) -> None:
        super().model_post_init(context)
        self.add_condition(
            name="decoder_not_wider_than_encoder",
            condition=lambda config: config.decoder_width <= config.encoder_width,
            description="A decoder wider than its encoder is not a bottleneck",
        )


def main() -> None:
    Registry.initialize()
    Registry.register_configuration(
        AutoencoderConfig(),
        name="autoencoder",
        namespace="tutorial",
        component=f"{__name__}.Autoencoder",
    )

    valid_keys, invalid_keys = Registry.dag_resolution()

    print(f"{len(valid_keys)} valid, {len(invalid_keys)} invalid\n")
    for key in sorted(valid_keys, key=str):
        built = Registry.from_key(key)
        print(f"  valid    {built.encoder_width:>4} -> {built.decoder_width:<4}")
    for key in sorted(invalid_keys, key=str):
        reason = (key.metadata or "").split("Message:")[-1].strip()
        print(f"  invalid  {', '.join(sorted(key.tags)):32s} {reason}")

    print(
        "\nOnly the valid keys stay in the registry, so `cmn-run` will not offer"
        "\nyou a combination that cannot work. The invalid ones are returned so"
        "\nthat a sweep can report what it skipped and why."
    )


if __name__ == "__main__":
    main()
