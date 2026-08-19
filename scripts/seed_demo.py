from sldforge.generator import build_radial_fixture

if __name__ == "__main__":
    print(build_radial_fixture().model_dump_json(indent=2))
