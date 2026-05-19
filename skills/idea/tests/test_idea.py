def test_no_args_exits_1(run):
    proc = run(expect_code=1)
    assert "Error:" in proc.stderr or "usage" in proc.stderr.lower()


def test_unknown_verb_exits_1(run):
    run("frobnicate", expect_code=1)
