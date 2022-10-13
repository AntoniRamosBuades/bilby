#!/usr/bin/env python
"""
Demonstration of how to use the :code:`bilby.core.sampler.FakeSampler` to
reweight a computationally cheap analysis to a more expensive one.

For this example, we simulate a signal using our high fidelity model
(:code:`IMRPhenomXPHM`) and analyze it using a model with higher-order
emission modes included (:code:`IMRPhenomXP`).
We then, reweight the result of the first step to obtain posteriors and
evidence estimates for the more expensive model.
We additionally change the prior for the second stage, because we can.
"""

from copy import deepcopy

import numpy as np
import bilby


outdir = "outdir"
label = "full"

np.random.seed(170808)

duration = 4
sampling_frequency = 1024

injection_parameters = dict(
    chirp_mass=36.0,
    mass_ratio=0.1,
    a_1=0.8,
    a_2=0.3,
    tilt_1=0.0,
    tilt_2=0.0,
    phi_12=1.7,
    phi_jl=0.3,
    luminosity_distance=2000.0,
    theta_jn=0.4,
    psi=0.659,
    phase=1.3,
    geocent_time=1126259642.413,
    ra=1.375,
    dec=-1.2108,
)

waveform_arguments = dict(
    waveform_approximant="IMRPhenomXPHM",
    reference_frequency=20.0,
    minimum_frequency=20.0,
)

waveform_generator = bilby.gw.WaveformGenerator(
    duration=duration,
    sampling_frequency=sampling_frequency,
    frequency_domain_source_model=bilby.gw.source.lal_binary_black_hole,
    waveform_arguments=waveform_arguments,
    parameter_conversion=bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
)

ifos = bilby.gw.detector.InterferometerList(["H1", "L1", "V1"])

ifos.set_strain_data_from_zero_noise(
    sampling_frequency=sampling_frequency,
    duration=duration,
    start_time=injection_parameters["geocent_time"] - 3,
)

ifos.inject_signal(
    waveform_generator=waveform_generator, parameters=injection_parameters
)

priors = bilby.gw.prior.BBHPriorDict()
for key in [
    "a_1",
    "a_2",
    "tilt_1",
    "tilt_2",
    "theta_jn",
    "psi",
    "ra",
    "dec",
    "phi_12",
    "phi_jl",
    "luminosity_distance",
]:
    priors[key] = injection_parameters[key]
del priors["mass_1"], priors["mass_2"]
priors["chirp_mass"] = bilby.core.prior.Uniform(30, 40, latex_label="$\\mathcal{M}$")
priors["mass_ratio"] = bilby.core.prior.Uniform(0.05, 0.25, latex_label="$q$")
priors["geocent_time"] = bilby.core.prior.Uniform(
    injection_parameters["geocent_time"] - 0.1,
    injection_parameters["geocent_time"] + 0.1,
    latex_label="$t_c$",
    unit="s",
)

waveform_generator.waveform_arguments["waveform_approximant"] = "IMRPhenomXP"

likelihood_1 = bilby.gw.GravitationalWaveTransient(
    interferometers=ifos, waveform_generator=waveform_generator
)

result_1 = bilby.run_sampler(
    likelihood=likelihood_1,
    priors=priors,
    sampler="nestle",
    nlive=250,
    injection_parameters=injection_parameters,
    outdir=outdir,
    label=f"{label}_XP",
    save="hdf5",
)

# update the waveform approximant to use our high-fidelity model
waveform_generator.waveform_arguments["waveform_approximant"] = "IMRPhenomXPHM"

likelihood_2 = bilby.gw.GravitationalWaveTransient(
    interferometers=ifos, waveform_generator=waveform_generator
)

sample_file = f"{result_1.outdir}/{result_1.label}_result.hdf5"

# update the mass prior to be uniform in component masses
priors_2 = deepcopy(priors)
priors_2["chirp_mass"] = bilby.gw.prior.UniformInComponentsChirpMass(30, 40)
priors_2["mass_ratio"] = bilby.gw.prior.UniformInComponentsMassRatio(0.05, 0.25)

result_2 = bilby.core.result.reweight(
    result_1,
    new_likelihood=likelihood_2,
    new_prior=priors_2,
    old_likelihood=likelihood_1,
    old_prior=priors,
    resume_file=f"{outdir}/importance_weights.txt",
    use_nested_samples=True,
)

bilby.core.result.plot_multiple([result_1, result_2])
