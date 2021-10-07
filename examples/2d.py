
import nengo
import numpy as np

model = nengo.Network()
with model:
    stimulus = nengo.Node(lambda t: np.sin(t))
    ens = nengo.Ensemble(n_neurons=10, dimensions=1)
    nengo.Connection(stimulus, ens)
    nengo.Probe

if __name__ == "__main__":
    import nengo_3d

    nengo_3d.GUI(filename=__file__, model=model, local_vars=locals()).start()
