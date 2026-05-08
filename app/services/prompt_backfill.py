def backfill_test_case_prompt_templates(db) -> int:
    from ..models import TestCase, TestType
    from .test_runner import _build_generated_prompt

    updated = 0
    test_types = {tt.id: tt for tt in db.query(TestType).all()}
    for tc in db.query(TestCase).all():
        if tc.user_prompt_template and tc.user_prompt_template.strip():
            continue
        tt = test_types.get(tc.test_type_id)
        if not tt:
            continue
        tc.user_prompt_template = _build_generated_prompt(tc, tt)
        updated += 1
    if updated:
        db.commit()
    return updated
