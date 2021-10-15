# Nengo 3d

3d interactive neural network visualization toolkit for Nengo simulator

python + Nengo + Blender

In development

## Install and run

Clone source of this repo and make sure you can `import nengo_3d`.

In `blender.exe` is not in path (to check just write `bledner.exe` in command line). If not, use `blender=...` argument
in `nengo_3d.GUI`.

### Run

Use snipped:

```python
if __name__ == "__main__":
    import nengo_3d

    nengo_3d.GUI(filename=__file__, model=model, local_vars=locals()).start()
```

## File structure

`nengo_3d` - python module to use in your project

`nengo_3d/nengo_app` - blender template

`nengo_3d/nengo_app/bl_nengo_3d` - blender addon (automatic installation)

`nengo_3d/nengo_app/dependencies` - scripts for installing addon and 3rt party modules

`nengo_3d/nengo_app/blender_pip_modules` - blender addon dependencies (automatic installation, when starting
nengo_3d.GUI)

## Issues

- [ ] do not store pointer directly to blender object, refer to them by name, it breaks undo system (almost done, todo _
  blender_object, and `axes.root`)
- [x] ~~performance in UI panels is not great. Advanced caching is needed or conversion to dedicated operators. Close
  addon panels that you do not use to improve performance~~
- [x] ~~re-test save model state and restoring connection~~
- [ ] lines example is not working
- [ ] allow for scrubbing data and stepping simulation even if reset is required