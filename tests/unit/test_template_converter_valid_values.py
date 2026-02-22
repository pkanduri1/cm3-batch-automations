from src.config.template_converter import TemplateConverter


def test_template_converter_parses_pipe_separated_valid_values(tmp_path):
    csv_file = tmp_path / "mapping.csv"
    csv_file.write_text(
        "Field Name,Data Type,Valid Values\n"
        "status,String,ACTIVE|INACTIVE|CLOSED\n",
        encoding="utf-8",
    )

    converter = TemplateConverter()
    mapping = converter.from_csv(str(csv_file), mapping_name="test_mapping", file_format="pipe_delimited")

    field = mapping["fields"][0]
    assert field["valid_values"] == ["ACTIVE", "INACTIVE", "CLOSED"]
    assert {"type": "in_list", "parameters": {"values": ["ACTIVE", "INACTIVE", "CLOSED"]}} in field["validation_rules"]


def test_template_converter_parses_comma_separated_valid_values(tmp_path):
    csv_file = tmp_path / "mapping.csv"
    csv_file.write_text(
        "Field Name,Data Type,Valid Values\n"
        "status,String,ACTIVE,INACTIVE,CLOSED\n",
        encoding="utf-8",
    )

    # Quote the value so CSV parser keeps it in one column
    csv_file.write_text(
        'Field Name,Data Type,Valid Values\nstatus,String,"ACTIVE,INACTIVE,CLOSED"\n',
        encoding="utf-8",
    )

    converter = TemplateConverter()
    mapping = converter.from_csv(str(csv_file), mapping_name="test_mapping", file_format="pipe_delimited")

    field = mapping["fields"][0]
    assert field["valid_values"] == ["ACTIVE", "INACTIVE", "CLOSED"]
