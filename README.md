# Nengo 3d

3d interactive neural network visualization toolkit for Nengo simulator

python + Nengo + Blender

In development

## Install and run


## Standing issues

- [ ] do not store pointer directly to blender object, refer to them by name, it breaks undo system
- [ ] performance in UI panels is not great. Advanced caching is needed or conversion to dedicated operators. Close addon panels that you do not use to improve performance
- [ ] re-test save model state and restoring connection
- [ ] allow for scrubbing data and stepping simulation even if reset is required