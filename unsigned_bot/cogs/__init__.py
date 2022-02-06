"""
Module for cogs.

Each submodule contains a cog with group specific slash commands.
"""

BOT_COMMANDS = {
    "general": {
        "description": "commands for general information",
        "faq": {
            "syntax": "/faq",
            "hint": "show important information"
        },
    },
    "data": {
        "description": "commands to get info about your unsig",
        "unsig": {
            "syntax": "/unsig + `unsig_number`",
            "hint": "show info for unsig with given number"
        },
        "metadata": {
            "syntax": "/metadata + `unsig_number`",
            "hint": "show data of unsig with given number"
        },
        "minted": {
            "syntax": "/minted + `minting_order`",
            "hint": "show unsig with given minting order"
        },
        "cert": {
            "syntax": "/cert + `unsig_number`",
            "hint": "show cert of unsig with given number"
        }
    },
    "geometry": {
        "description": "commands for geometrical analysis",
        "pattern-combo": {
            "syntax": "/pattern-combo",
            "hint": "count unsigs with given pattern combo"
        },
        "forms": {
            "syntax": "/forms",
            "hint": "show unsigs with given form"            
        }
    },
    "structure": {
        "description": "commands to deconstruct your unsig",
        "evo": {
            "syntax": "/evo + `unsig_number`",
            "hint": "show composition of your unsig"
        },
        "invo": {
            "syntax": "/invo + `unsig_number`",
            "hint": "show ingredients of your unsig"
        },
        "subs": {
            "syntax": "/subs + `unsig_number`",
            "hint": "show subpattern of your unsig"
        }
    },
    "colors": {
        "description": "commands for color analysis",
        "colors": {
            "syntax": "/colors + `unsig_number`",
            "hint": "show output colors of your unsig"
        },
        "color-ranking": {
            "syntax": "/color-ranking",
            "hint": "show color ranking"
        }
    },
    "ownership": {
        "description": "commands for ownership of unsigs",
        "owner": {
            "syntax": "/owner + `unsig_number`",
            "hint": "show wallet of given unsig"
        }
    },
    "market": {
        "description": "commands for offers and sales",
        "sell": {
            "syntax": "/sell + `unsig_number` + `price`",
            "hint": "offer your unsig for sale"
        },
        "floor": {
            "syntax": "/floor",
            "hint": "show cheapest unsigs on marketplace"
        },
        "sales": {
            "syntax": "/sales",
            "hint": "show sold unsigs on marketplace"
        },
        "like": {
            "syntax": "/like + `unsig_number`",
            "hint": "show related unsigs sold"
        },
        "matches": {
            "syntax": "/matches + `unsig_number`",
            "hint": "show available matches on marketplace"
        }
    },
    "collection": {
        "description": "commands for your unsig collection",
        "show": {
            "syntax": "/show + `unsig_numbers`",
            "hint": "show your unsig collection"
        },
        "siblings": {
            "syntax": "/siblings + `unsig_number`",
            "hint": "show siblings of your unsig"
        }
    }
}