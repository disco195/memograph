import random

from mg.io import print, input


def run_learn(deck, hand):
    print("introduce some new cards...")
    n = len(hand)
    if n == 0:
        print("no new cards! try drilling some old ones.")
        return
    random.shuffle(hand)
    for i, card in enumerate(hand, 1):
        print(f"<bold>**<reset> learn {i}/{n} <bold>**<reset>")
        face, back = card
        if card.topics(): print("topics:", card.topics())
        print("prompt:", face.label())
        face.media()
        input("return:")
        print("answer:", back.label())
        back.media()
        instructions = "easy (g+↵) | medium (↵) | hard (h+↵)"
        rating = input("rating:", r=instructions)
        if rating == "g":
            card.initialise([1, 1,  2*24*60*60])
        elif rating == "h":
            card.initialise([1, 1,        1*60])
        else:
            card.initialise([1, 1,     1*60*60])
    print("saving.")
    deck.save()
