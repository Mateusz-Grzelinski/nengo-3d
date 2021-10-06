# Nengo 3d

3d interactive neural network visualization toolkit for Nengo simulator

python + Nengo + Blender

In development

## Install and run

Clone source of this repo and make sure you can `import nengo_3d`.

In `blender.exe` is not in path (to check just write `bledner.exe` in command line). If not use `blender=...` argument
in `nengo_3d.GUI`.

### Run

Use snipped:

```python
if __name__ == "__main__":
    import nengo_3d

    nengo_3d.GUI(filename=__file__, model=model, local_vars=locals()).start()
```

## File structure

``

## Standing issues

- [ ] do not store pointer directly to blender object, refer to them by name, it breaks undo system
- [ ] performance in UI panels is not great. Advanced caching is needed or conversion to dedicated operators. Close
  addon panels that you do not use to improve performance
- [ ] re-test save model state and restoring connection
- [ ] allow for scrubbing data and stepping simulation even if reset is required