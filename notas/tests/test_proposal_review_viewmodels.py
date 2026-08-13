from django.test import SimpleTestCase

from notas.presentation.proposals.proposal_review_viewmodels import (
    build_proposal_review_vm,
)


class ProposalReviewViewModelTests(SimpleTestCase):
    def test_build_review_vm_for_create_meal_proposal(self):
        proposal = {
            "id": 10,
            "title": "Propuesta comida IA",
            "summary": "Comida propuesta.",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": None,
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "targets": {
                "protein": 60,
            },
            "proposed_payload": {
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 1,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
            "validation_summary": {
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_meal",
                },
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "kpis": {
                            "protein": 62,
                            "total_kcal": 312.8,
                        },
                    },
                    "dailyplan": None,
                },
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertEqual(vm.proposal_id, 10)
        self.assertEqual(vm.title, "Propuesta comida IA")
        self.assertEqual(vm.dailyplan_id, 128)
        self.assertEqual(vm.dailyplan_name, "Menú Dia Entrenamiento")
        self.assertEqual(vm.status.status, "pending_review")
        self.assertTrue(vm.status.is_reviewable)
        self.assertFalse(vm.status.is_final)

        self.assertEqual(vm.payload.intent, "create_meal")
        self.assertTrue(vm.payload.is_create_meal)
        self.assertFalse(vm.payload.is_create_dailyplan)
        self.assertEqual(vm.payload.targets, {"protein": 60})
        self.assertEqual(
            vm.payload.simulation["meal"]["kpis"]["protein"],
            62,
        )

    def test_build_review_vm_for_create_dailyplan_proposal(self):
        proposal = {
            "id": 20,
            "title": "Propuesta DailyPlan IA",
            "summary": "",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": None,
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "targets": {
                "protein": 190,
                "total_kcal": 2800,
            },
            "proposed_payload": {
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día IA",
                    "meals": [],
                },
            },
            "validation_summary": {
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_dailyplan",
                },
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
                    "dailyplan": {
                        "name": "Día IA",
                        "kpis": {
                            "protein": 2,
                            "total_kcal": 34,
                        },
                    },
                },
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertEqual(vm.payload.intent, "create_dailyplan")
        self.assertFalse(vm.payload.is_create_meal)
        self.assertTrue(vm.payload.is_create_dailyplan)
        self.assertEqual(
            vm.payload.simulation["dailyplan"]["kpis"]["total_kcal"],
            34,
        )

    def test_build_review_vm_handles_missing_optional_payload_fields(self):
        proposal = {
            "id": 30,
            "title": "Legacy proposal",
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
        }

        vm = build_proposal_review_vm(proposal)

        self.assertEqual(vm.proposal_id, 30)
        self.assertEqual(vm.title, "Legacy proposal")
        self.assertIsNone(vm.payload.intent)
        self.assertFalse(vm.payload.is_create_meal)
        self.assertFalse(vm.payload.is_create_dailyplan)
        self.assertEqual(vm.payload.proposed_payload, {})
        self.assertIsNone(vm.payload.simulation)
        self.assertEqual(vm.payload.targets, {})

    def test_review_vm_as_dict_is_template_friendly(self):
        proposal = {
            "id": 40,
            "title": "Propuesta comida IA",
            "summary": "",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": None,
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "targets": {},
            "proposed_payload": {
                "intent": "create_meal",
            },
            "validation_summary": {
                "simulation": {
                    "intent": "create_meal",
                },
            },
        }

        data = build_proposal_review_vm(proposal).as_dict()

        self.assertEqual(
            data,
            {
                "proposal_id": 40,
                "title": "Propuesta comida IA",
                "summary": "",
                "dailyplan_id": 128,
                "dailyplan_name": "Menú Dia Entrenamiento",
                "created_by_username": "felipe",
                "reviewed_by_username": None,
                "received_at_label": "",
                "is_read": False,
                "status": {
                    "status": "pending_review",
                    "label": "Pendiente",
                    "is_reviewable": True,
                    "is_final": False,
                    "is_approved": False,
                    "is_applied": False,
                },
                "payload": {
                    "intent": "create_meal",
                    "entity_title": "Comida en la propuesta",
                    "attachments": [
                        {
                            "kind": "meal",
                            "label": "Comida propuesta",
                            "name": "Propuesta comida IA",
                            "icon": "utensils",
                        }
                    ],
                    "is_create_meal": True,
                    "is_create_dailyplan": False,
                    "is_apply_supported": True,
                    "proposed_payload": {
                        "intent": "create_meal",
                    },
                    "simulation": {
                        "intent": "create_meal",
                    },
                    "targets": {},
                    "meal": None,
                    "dailyplan": None,
                },
                "can_apply": False,
                "subject_context_warning": {
                    "requires_warning": False,
                    "source": "",
                    "source_label": "Contexto no especificado",
                    "ppk_weight_source": "",
                    "ppk_weight_source_label": "Peso no especificado",
                    "calculation_weight_kg": None,
                    "calculation_weight_label": "Peso externo no especificado",
                    "title": "Propuesta calculada con datos externos",
                    "message": (
                        "Esta propuesta fue calculada con datos distintos a tu ficha personal. "
                        "Si la guardas en tu librería, My Scoope conservará las calorías y gramos "
                        "de macros propuestos, pero los indicadores dependientes de tu perfil, "
                        "como PPK, se mostrarán usando el peso registrado en tu ficha personal."
                    ),
                },
                "applied_result": None,
                "iteration_trace": None,
            }
        )
    
    def test_build_review_vm_includes_create_meal_render_data(self):
        proposal = {
            "id": 50,
            "title": "Comida AI",
            "summary": "Comida propuesta.",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": None,
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "targets": {
                "protein": 60,
                "total_kcal": 500,
            },
            "proposed_payload": {
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [],
                },
            },
            "validation_summary": {
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_meal",
                },
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [
                            {
                                "food_id": 10,
                                "food_name": "Pechuga pollo",
                                "quantity": 200,
                                "unit": "g",
                                "protein": 62,
                                "carbs": 0,
                                "fat": 7.2,
                                "total_kcal": 312.8,
                            },
                        ],
                        "kpis": {
                            "total_kcal": 312.8,
                            "protein": 62,
                            "carbs": 0,
                            "fat": 7.2,
                            "ppk": 0.62,
                            "alloc_protein": 79.28,
                            "alloc_carbs": 0,
                            "alloc_fat": 20.72,
                        },
                    },
                    "dailyplan": None,
                },
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertIsNotNone(vm.payload.meal)
        self.assertEqual(vm.payload.meal.name, "Almuerzo IA")
        self.assertEqual(len(vm.payload.meal.foods), 1)

        food = vm.payload.meal.foods[0]

        self.assertEqual(food.food_id, 10)
        self.assertEqual(food.food_name, "Pechuga pollo")
        self.assertEqual(food.quantity, 200.0)
        self.assertEqual(food.unit, "g")
        self.assertEqual(food.protein, 62.0)
        self.assertEqual(food.total_kcal, 312.8)

        self.assertIsNotNone(vm.payload.meal.kpis)
        self.assertEqual(vm.payload.meal.kpis.protein, 62.0)
        self.assertEqual(vm.payload.meal.kpis.total_kcal, 312.8)
        self.assertEqual(vm.payload.meal.kpis.ppk, 0.62)

        row = vm.payload.meal.card["table"]["items"][0]["rel"]
        self.assertAlmostEqual(row["alloc_protein"], 100)
        self.assertAlmostEqual(row["alloc_fat"], 100)
        self.assertAlmostEqual(sum(row["kcal_distribution"].values()), 100)
        self.assertNotEqual(
            row["alloc_protein"],
            row["kcal_distribution"]["protein"],
        )


    def test_build_review_vm_includes_create_dailyplan_render_data(self):
        proposal = {
            "id": 60,
            "title": "Plan AI",
            "summary": "DailyPlan propuesto.",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": None,
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "targets": {
                "protein": 190,
                "total_kcal": 2800,
            },
            "proposed_payload": {
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [],
                },
            },
            "validation_summary": {
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_dailyplan",
                },
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
                    "dailyplan": {
                        "name": "Día entrenamiento IA",
                        "meals": [
                            {
                                "hour": "09:00",
                                "note": "Desayuno",
                                "meal": {
                                    "name": "Desayuno IA",
                                    "foods": [
                                        {
                                            "food_id": 128,
                                            "food_name": "a nuevo egg TEST",
                                            "quantity": 200,
                                            "unit": "g",
                                            "protein": 2,
                                            "carbs": 2,
                                            "fat": 2,
                                            "total_kcal": 34,
                                        },
                                    ],
                                    "kpis": {
                                        "total_kcal": 34,
                                        "protein": 2,
                                        "carbs": 2,
                                        "fat": 2,
                                        "ppk": 0.02,
                                        "alloc_protein": 23.52,
                                        "alloc_carbs": 23.52,
                                        "alloc_fat": 52.94,
                                    },
                                },
                            },
                        ],
                        "kpis": {
                            "total_kcal": 34,
                            "protein": 2,
                            "carbs": 2,
                            "fat": 2,
                            "ppk": 0.02,
                            "alloc_protein": 23.52,
                            "alloc_carbs": 23.52,
                            "alloc_fat": 52.94,
                        },
                    },
                },
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertIsNone(vm.payload.meal)
        self.assertIsNotNone(vm.payload.dailyplan)

        dailyplan = vm.payload.dailyplan

        self.assertEqual(dailyplan.name, "Día entrenamiento IA")
        self.assertEqual(len(dailyplan.meals), 1)
        self.assertIsNotNone(dailyplan.kpis)
        self.assertEqual(dailyplan.kpis.total_kcal, 34.0)
        self.assertEqual(dailyplan.kpis.protein, 2.0)

        dailyplan_meal = dailyplan.meals[0]

        self.assertEqual(dailyplan_meal.hour, "09:00")
        self.assertEqual(dailyplan_meal.note, "Desayuno")
        self.assertEqual(dailyplan_meal.meal.name, "Desayuno IA")
        self.assertEqual(len(dailyplan_meal.meal.foods), 1)

        food = dailyplan_meal.meal.foods[0]

        self.assertEqual(food.food_id, 128)
        self.assertEqual(food.food_name, "a nuevo egg TEST")
        self.assertEqual(food.quantity, 200.0)
        self.assertEqual(food.total_kcal, 34.0)

        row = dailyplan.card["table"]["items"][0]["rel"]
        self.assertAlmostEqual(row["alloc_protein"], 100)
        self.assertAlmostEqual(row["alloc_carbs"], 100)
        self.assertAlmostEqual(row["alloc_fat"], 100)
        self.assertAlmostEqual(sum(row["kcal_distribution"].values()), 100)
        self.assertNotEqual(
            row["alloc_protein"],
            row["kcal_distribution"]["protein"],
        )

    def test_build_review_vm_can_apply_approved_create_meal(self):
        proposal = {
            "id": 70,
            "title": "Comida AI",
            "summary": "",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": "felipe",
            "status": "approved",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": None,
            "targets": {},
            "proposed_payload": {
                "intent": "create_meal",
            },
            "validation_summary": {},
        }

        vm = build_proposal_review_vm(proposal)

        self.assertTrue(vm.status.is_approved)
        self.assertFalse(vm.status.is_applied)
        self.assertTrue(vm.payload.is_apply_supported)
        self.assertTrue(vm.can_apply)


    def test_build_review_vm_can_apply_approved_create_dailyplan(self):
        proposal = {
            "id": 71,
            "title": "Plan AI",
            "summary": "",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": "felipe",
            "status": "approved",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": None,
            "targets": {},
            "proposed_payload": {
                "intent": "create_dailyplan",
            },
            "validation_summary": {},
        }

        vm = build_proposal_review_vm(proposal)

        self.assertTrue(vm.status.is_approved)
        self.assertTrue(vm.payload.is_apply_supported)
        self.assertTrue(vm.can_apply)


    def test_build_review_vm_cannot_apply_pending_review(self):
        proposal = {
            "id": 72,
            "title": "Comida AI",
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "applied_at": None,
            "proposed_payload": {
                "intent": "create_meal",
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertFalse(vm.can_apply)


    def test_build_review_vm_cannot_apply_unsupported_intent(self):
        proposal = {
            "id": 73,
            "title": "Legacy",
            "status": "approved",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": None,
            "proposed_payload": {
                "intent": "adjust_dailyplan_to_targets",
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertFalse(vm.payload.is_apply_supported)
        self.assertFalse(vm.can_apply)


    def test_build_review_vm_cannot_apply_already_applied(self):
        proposal = {
            "id": 74,
            "title": "Comida AI",
            "status": "applied",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": "2026-05-11T23:59:00+00:00",
            "proposed_payload": {
                "intent": "create_meal",
            },
        }

        vm = build_proposal_review_vm(proposal)

        self.assertTrue(vm.status.is_applied)
        self.assertTrue(vm.payload.is_apply_supported)
        self.assertFalse(vm.can_apply)

    def test_build_review_vm_includes_applied_meal_result(self):
        proposal = {
            "id": 80,
            "title": "Comida AI",
            "status": "applied",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": "2026-05-11T23:59:00+00:00",
            "proposed_payload": {
                "intent": "create_meal",
            },
            "audit_events": [
                {
                    "action": "applied",
                    "metadata": {
                        "meal_id": 123,
                        "meal_name": "Almuerzo IA",
                    },
                },
            ],
        }

        vm = build_proposal_review_vm(proposal)

        self.assertIsNotNone(vm.applied_result)
        self.assertEqual(vm.applied_result.kind, "meal")
        self.assertEqual(vm.applied_result.object_id, 123)
        self.assertEqual(vm.applied_result.object_name, "Almuerzo IA")
        self.assertEqual(vm.applied_result.detail_url_name, "meal_detail")
        self.assertFalse(vm.can_apply)


    def test_build_review_vm_includes_applied_dailyplan_result(self):
        proposal = {
            "id": 81,
            "title": "Plan AI",
            "status": "applied",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": "2026-05-11T23:59:00+00:00",
            "proposed_payload": {
                "intent": "create_dailyplan",
            },
            "audit_events": [
                {
                    "action": "applied",
                    "metadata": {
                        "dailyplan_id": 456,
                        "dailyplan_name": "Día entrenamiento IA",
                    },
                },
            ],
        }

        vm = build_proposal_review_vm(proposal)

        self.assertIsNotNone(vm.applied_result)
        self.assertEqual(vm.applied_result.kind, "dailyplan")
        self.assertEqual(vm.applied_result.object_id, 456)
        self.assertEqual(vm.applied_result.object_name, "Día entrenamiento IA")
        self.assertEqual(vm.applied_result.detail_url_name, "dailyplan_detail")
        self.assertFalse(vm.can_apply)

    def test_build_review_vm_includes_iteration_trace(self):
        proposal = {
            "id": 90,
            "title": "Plan IA v2",
            "summary": "Propuesta actualizada.",
            "status": "pending_review",
            "is_reviewable": True,
            "is_final": False,
            "proposed_payload": {
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Plan IA v2",
                    "meals": [],
                },
            },
            "current_snapshot": {
                "iteration": {
                    "previous_proposal_id": 89,
                    "user_message": "sin arroz y más proteína",
                    "command_labels": ["Evitar arroz", "Subir proteína objetivo"],
                    "command_set": {
                        "commands": [
                            {"kind": "avoid_food", "value": "arroz"},
                            {"kind": "adjust_target", "metric": "protein", "direction": "increase"},
                        ],
                    },
                },
            },
            "validation_summary": {},
        }

        vm = build_proposal_review_vm(proposal)

        self.assertIsNotNone(vm.iteration_trace)
        self.assertEqual(vm.iteration_trace.previous_proposal_id, 89)
        self.assertEqual(vm.iteration_trace.user_message, "sin arroz y más proteína")
        self.assertEqual(vm.iteration_trace.command_count, 2)
        self.assertEqual(
            vm.iteration_trace.command_labels,
            ["Evitar arroz", "Subir proteína objetivo"],
        )
        self.assertEqual(vm.iteration_trace.previous_proposal_url, "/app/proposals/89/")
        self.assertEqual(vm.iteration_trace.short_label, "Evitar arroz · Subir proteína objetivo")

    def test_build_review_vm_exposes_external_subject_warning(self):
        proposal = {
            "id": 73,
            "title": "Plan externo",
            "summary": "Plan calculado para otra persona.",
            "dailyplan_id": 128,
            "dailyplan_name": "Menú Dia Entrenamiento",
            "created_by_username": "felipe",
            "reviewed_by_username": "felipe",
            "status": "approved",
            "is_reviewable": False,
            "is_final": True,
            "applied_at": None,
            "targets": {
                "subject_context": {
                    "source": "external_chat_data",
                    "ppk_weight_source": "external_subject_weight",
                    "requires_library_ppk_warning": True,
                    "calculation_weight_kg": 70,
                },
            },
            "proposed_payload": {
                "intent": "create_dailyplan",
            },
            "validation_summary": {},
        }

        vm = build_proposal_review_vm(proposal)

        self.assertTrue(vm.subject_context_warning.requires_warning)
        self.assertEqual(
            vm.subject_context_warning.source_label,
            "Datos externos del chat",
        )
        self.assertEqual(vm.subject_context_warning.calculation_weight_label, "70 kg")
