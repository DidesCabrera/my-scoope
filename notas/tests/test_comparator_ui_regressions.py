from pathlib import Path
from unittest import TestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPARATOR_TEMPLATE = PROJECT_ROOT / "notas" / "templates" / "notas" / "comparators" / "detail.html"
COMPARATOR_JS = PROJECT_ROOT / "notas" / "static" / "notas" / "js" / "comparators.js"


class ComparatorUiRegressionTests(TestCase):
    def test_remove_button_is_rendered_inside_each_selector_heading(self):
        template = COMPARATOR_TEMPLATE.read_text()
        heading_start = template.index('class="comparator-selector__heading"')
        heading_end = template.index('<label class="comparator-field"', heading_start)
        heading_markup = template[heading_start:heading_end]

        self.assertIn('data-comparator-remove', heading_markup)
        self.assertIn('name="remove_index"', heading_markup)
        self.assertIn('value="{{ forloop.counter0 }}"', heading_markup)
        self.assertIn('data-lucide="trash-2"', heading_markup)
        self.assertIn('not vm.content.can_remove_selection', heading_markup)

    def test_saved_detail_starts_in_read_mode_and_has_edit_mode_controls(self):
        template = COMPARATOR_TEMPLATE.read_text()

        self.assertIn('data-comparator-saved-detail-form', template)
        self.assertIn('is-read-mode', template)
        self.assertIn('data-comparator-edit-mode-input', template)
        self.assertIn('data-comparator-edit-toggle', template)
        self.assertIn('Editar comparación', template)
        self.assertIn('data-comparator-save-changes', template)

    def test_save_comparison_button_is_visible_only_after_first_comparison(self):
        template = COMPARATOR_TEMPLATE.read_text()
        save_button_index = template.index('value="save_comparison"')
        gate_index = template.rfind('{% if vm.content.is_ready %}', 0, save_button_index)
        saved_detail_else_index = template.rfind('{% else %}', 0, save_button_index)

        self.assertGreater(gate_index, saved_detail_else_index)
        self.assertIn('Guardar comparacion', template)
        self.assertIn('Guardar cambios', template)

    def test_comparator_javascript_preserves_saved_edit_mode_after_reload_actions(self):
        script = COMPARATOR_JS.read_text()

        self.assertIn('function ensureEditModeInput()', script)
        self.assertIn('editModeInput.name = "edit"', script)
        self.assertIn('editModeInput.value = "1"', script)
        self.assertIn('form.classList.remove("is-read-mode")', script)
        self.assertIn('syncRemoveButtons(form)', script)

    def test_comparator_javascript_trash_visibility_contract(self):
        script = COMPARATOR_JS.read_text()

        self.assertIn('selectors.length > 2', script)
        self.assertIn('!form.classList.contains("is-read-mode")', script)
        self.assertIn('removeButton.classList.toggle("is-hidden", !canRemove)', script)
        self.assertIn('removeButton.disabled = !canRemove', script)
