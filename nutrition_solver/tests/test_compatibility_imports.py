from django.test import SimpleTestCase

import notas.application.nutrition_engine.contracts as legacy_contracts
import notas.application.nutrition_engine.models as legacy_models
import notas.application.nutrition_engine.portion_solver as legacy_portion_solver
import notas.application.nutrition_engine.validators as legacy_validators
import nutrition_solver.application.contracts as solver_contracts
import nutrition_solver.application.portion_solver as solver_portion_solver
import nutrition_solver.application.validators as solver_validators
import nutrition_solver.domain.models as solver_models


class NutritionSolverCompatibilityImportTests(SimpleTestCase):
    def test_legacy_model_imports_point_to_new_solver_domain(self):
        self.assertIs(legacy_models.MacroTarget, solver_models.MacroTarget)
        self.assertIs(legacy_models.PortionBounds, solver_models.PortionBounds)
        self.assertIs(legacy_models.SolverFood, solver_models.SolverFood)
        self.assertIs(legacy_models.PortionSolverResult, solver_models.PortionSolverResult)

    def test_legacy_contract_imports_point_to_new_solver_contracts(self):
        self.assertIs(legacy_contracts.OptimizationInput, solver_contracts.OptimizationInput)
        self.assertIs(legacy_contracts.OptimizationResult, solver_contracts.OptimizationResult)
        self.assertIs(legacy_contracts.OptimizationStatus, solver_contracts.OptimizationStatus)
        self.assertIs(legacy_contracts.SolverConstraint, solver_contracts.SolverConstraint)
        self.assertIs(
            legacy_contracts.assess_optimization_status,
            solver_contracts.assess_optimization_status,
        )

    def test_legacy_contract_optimizer_wrapper_points_to_solver_app(self):
        self.assertTrue(callable(legacy_contracts.optimize_meal_portions))
        self.assertIs(
            legacy_contracts.optimize_meal_portions,
            solver_contracts.optimize_meal_portions,
        )

    def test_legacy_portion_solver_imports_point_to_solver_app(self):
        self.assertIs(legacy_portion_solver.PortionSolverConfig, solver_portion_solver.PortionSolverConfig)
        self.assertIs(legacy_portion_solver.PortionSolverError, solver_portion_solver.PortionSolverError)
        self.assertIs(legacy_portion_solver.solve_meal_portions, solver_portion_solver.solve_meal_portions)

    def test_legacy_validator_imports_point_to_solver_app(self):
        self.assertIs(legacy_validators.NutritionValidationIssue, solver_validators.NutritionValidationIssue)
        self.assertIs(legacy_validators.PortionValidationInput, solver_validators.PortionValidationInput)
        self.assertIs(legacy_validators.compare_macro_targets, solver_validators.compare_macro_targets)
        self.assertIs(
            legacy_validators.validate_generated_dailyplan,
            solver_validators.validate_generated_dailyplan,
        )
