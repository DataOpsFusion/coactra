import coactra.model as model_mod
from coactra import ModelProfile, ModelResolver, ModelRoute


def test_model_exports_present_on_root_and_module():
    assert model_mod.ModelProfile is ModelProfile
    assert model_mod.ModelRoute is ModelRoute
    assert model_mod.ModelResolver is ModelResolver
