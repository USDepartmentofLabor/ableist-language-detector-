"""Module with functions to extract ability vs. skills terms from ONET data."""

from typing import Iterable, Tuple, List
from collections import Counter
from pathlib import Path
import click
import pandas as pd
import spacy


nlp = spacy.load("en_core_web_sm")


def get_verbs(spacy_doc: spacy.tokens.Doc) -> List[spacy.tokens.Token]:
    """Return a list of verb lemmas within a given document.

    Parameters
    ----------
    spacy_doc : spacy.tokens.Doc
        spaCy document to parse

    Returns
    -------
    List[spacy.tokens.Token]
        List of verb lemmas within the document
    """
    # TODO: Consider retuning the token instead, which contains the raw text as well
    # as the lemma
    verbs = [token.lemma_ for token in spacy_doc if token.pos_ == "VERB"]
    return verbs


def get_abilities(df: pd.DataFrame) -> pd.DataFrame:
    """Given the base content reference dataframe, return the rows that reference
    specific ability descriptions only.

    Parameters
    ----------
    df : pd.DataFrame
        Content model reference dataframe

    Returns
    -------
    pd.DataFrame
        Dataframe containing specific ablities and their descriptions
    """
    # section 1.A.*; abilities are element IDs with 9 elements
    # (fewer than 9 = subcategories)
    abilities_df = df[
        (df["Element ID"].str.startswith("1.A")) & (df["Element ID"].str.len() == 9)
    ]
    return abilities_df


def get_skills(df: pd.DataFrame) -> pd.DataFrame:
    """Given the base content reference dataframe, return the rows that reference
    specific skill descriptions only.

    Parameters
    ----------
    df : pd.DataFrame
        Content model reference dataframe

    Returns
    -------
    pd.DataFrame
        Dataframe containing specific skills and their descriptions
    """
    # either section 2.A or 2.B and element ID = 7 characters long
    skills_df = df[
        (
            (df["Element ID"].str.startswith("2.A"))
            | (df["Element ID"].str.startswith("2.B"))
        )
        & (df["Element ID"].str.len() == 7)
    ]
    return skills_df


def get_representative_terms(
    abilities_corpus: Iterable[str], skills_corpus: Iterable[str]
) -> Tuple[list, list]:
    # Intialize empty lists to store all the verbs extracted from the docs
    abilities_verbs = []
    skills_verbs = []

    # For each description, get the verbs and append them to the master list
    # TODO: Could refine by only retrieving verbs that occur at the start of the
    # description, i.e. only capture the main verb used in the skill/ability
    for doc in nlp.pipe(abilities_corpus):
        abilities_verbs.extend(get_verbs(doc))
    for doc in nlp.pipe(skills_corpus):
        skills_verbs.extend(get_verbs(doc))

    # Get counts for each verb; will be useful for ranking later
    abilities_verbs_counter = Counter(abilities_verbs)
    skills_verbs_counter = Counter(skills_verbs)

    # Compute the set difference and sort by term frequency
    # TODO: Could implement something more sophisticated/closer to TF-IDF that looks at
    # how often a term occurs in abilities vs. skills--impact would be to expand the
    # term list to include terms that occurred in both, but occurred much more
    # frequently in one than another
    unique_abilities_verbs = sorted(
        list(set(abilities_verbs).difference(skills_verbs)),
        key=lambda x: -abilities_verbs_counter[x],
    )
    unique_skills_verbs = sorted(
        list(set(skills_verbs).difference(abilities_verbs)),
        key=lambda x: -skills_verbs_counter[x],
    )
    return unique_abilities_verbs, unique_skills_verbs


@click.command()
@click.option(
    "--data_path",
    "-d",
    type=str,
    required=True,
    help=(
        "Local path to raw O*Net Content Model Reference document. Download from: "
        "https://www.onetcenter.org/dictionary/25.2/text/content_model_reference.html"
    ),
)
@click.option(
    "--output_dir",
    "-o",
    type=str,
    required=True,
    help="Path to local directory to save skills and abilities terms lists.",
)
def main(data_path, output_dir):
    """Extract representative terms for abilities and skills."""
    output_path = Path(output_dir)
    output_path.mkdir(
        parents=True, exist_ok=True
    )  # Create the subdir(s) if they don't already exist

    df = pd.read_csv(data_path, delimiter="\t")
    abilities_df = get_abilities(df)
    skills_df = get_skills(df)

    unique_abilities_verbs, unique_skills_verbs = get_representative_terms(
        abilities_df.Description, skills_df.Description
    )

    with open(output_path / "abilities_verbs.txt", "w") as abilities_out:
        abilities_out.writelines([f"{v}\n" for v in unique_abilities_verbs])

    with open(output_path / "skills_verbs.txt", "w") as skills_out:
        skills_out.writelines([f"{v}\n" for v in unique_skills_verbs])


if __name__ == "__main__":
    main()
