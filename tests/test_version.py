import fixgw

def test_fixgw_version(capsys):
    import fixgw.version

    # Capture the output
    captured = capsys.readouterr()

    # Assert the output is as expected
    assert captured.out.strip() == fixgw.__version__
