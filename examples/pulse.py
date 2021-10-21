import nengo

def pulse(t):
    if t < 0.05:
        return 1
    return 0


model = nengo.Network()
with model:
    stimulus_B = nengo.Node(pulse)
    ens = nengo.Ensemble(n_neurons=10, dimensions=1)
    nengo.Connection(stimulus_B, ens)

if __name__ == "__main__":
    import nengo_3d

    nengo_3d.GUI(filename=__file__, model=model, local_vars=locals()).start()
    # nengo_3d.GUI(__file__).start()
