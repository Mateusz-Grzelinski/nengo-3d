import os
import sys

import nengo

import numpy as np

try:
    from cogsci17_semflu.models.wta_semflu import SemFlu
except ImportError as e:
    print(e.msg +
        '\nTo run this file you must download and follow instructions from the source of paper "A Biologically '
        'Constrained Model of Semantic Memory Search". It is a bit time consuming but overall pretty easy.\n'
        'https://github.com/ctn-archive/kajic-cogsci2017',
        file=sys.stderr,
    )
    exit(1)

amat = 'ngram_mat'
wta_th = 0.3  # args.th[0]

# Model parameters
d = 256  # dimensionality of vectors
sim_len = 20  # simulation length
seed_start = 0
nr_seeds = 141  # number of simulations
nr_resp = 36  # nr of responses to process

# dir-name to store simulations
fname = '{}_{}r_{}d_{}th_{}n_157w'.format(
    amat, nr_seeds, d, wta_th, nr_resp)
print(amat, wta_th, fname)

seeds = np.arange(seed_start, nr_seeds)

base_dir = os.path.dirname(__file__)
results_dir = os.path.join(base_dir, 'data', fname)

# for seed in seeds:
seed = 0
sem_flu = SemFlu()
sem_flu.model  # actual model source
model: nengo.spa.SPA = sem_flu.make_model(d=d,
                                          seed=seed,
                                          sim_len=sim_len,
                                          wta_th=wta_th,
                                          amat=amat,
                                          data_dir=results_dir,
                                          backend='nengo')

if __name__ == "__main__":
    import nengo_3d

    # nengo.spa.enable_spa_params(model)
    nengo_3d.GUI(
        filename=__file__, model=model, local_vars=locals(),
        # tag='goals',
        tag='wta',
        # tag='general',
        # tag = 'overview',
    ).start()
