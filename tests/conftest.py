from hypothesis import settings

# Real work runs inside some properties; a timing deadline would turn a slow CI runner into a flake.
settings.register_profile("inkgrid", deadline=None)
settings.load_profile("inkgrid")
