import pandas as pd
from misc.publish_data import dict_to_cluster_list


def test_dict_to_cluster_list():
    assert sorted(dict_to_cluster_list("{'a': 'x', 'b': 'x', 'c': 'y'}")) == ['x', 'y']

    assert dict_to_cluster_list("{}") == []

    assert dict_to_cluster_list(None) == []

    print("All tests passed!")


def test_publish_data():
    df = pd.read_csv(
        "project_code/MarkdownConverter/data/csv/2026-01-30_combined_projects_with_term_dictionaries.csv",
        sep=";",
        nrows=5
    )

    df["Art"] = df["Art"].apply(dict_to_cluster_list)
    df["Einsatzbereich"] = df["Einsatzbereich"].apply(dict_to_cluster_list)

    assert all(isinstance(x, list) for x in df["Art"])
    assert all(isinstance(x, list) for x in df["Einsatzbereich"])

    print(f"Publish data test passed with {len(df)} rows")


if __name__ == "__main__":
    test_dict_to_cluster_list()
    test_publish_data()
