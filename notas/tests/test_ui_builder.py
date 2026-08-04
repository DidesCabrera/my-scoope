from django.test import TestCase

from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import PROFILE_VIEWMODE


class UIBuildersTests(TestCase):

    def test_build_ui_vm_for_profile_populates_navigation_metadata(self):
        ui = build_ui_vm(PROFILE_VIEWMODE)

        self.assertEqual(ui.nav_root, "profile")
        self.assertEqual(ui.icon, "circle-user-round")
        self.assertEqual(ui.section_label, "Tools")
        self.assertEqual(ui.page_icon, "circle-user-round")