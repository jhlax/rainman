# redis database schema

* `status`: layer 1 control status indicator
    * `uninit`: uninitialized; if the database is empty, this is default
    * `staging`: intermediate staging status; setting decks, players
    * `bets`: placing bets
    * `dealing`: dealing cards to available players
        * `dealing_<player-id>`: dealing the cards to a player
    * `bust`: bust status
        * `bust_<player-id>`: bust status for a player
        * `bust_0`: house busts
    * `player_moves`: player move status
        * `player_<player-id>_move`: a players move session
        * `player_<player-id>_blackjack`: a player blackjacks!
    * `sum`: summations status
        * `sum_<player-id>`: calculate the sum for a players hand
    * `hit_<player-id>`: hit for a player
    * `stay_<player-id>`: stays for a player

    > there are more for this potentially

* `player/:...`: player informations
* `house:...`: house information
* `bets:...`: bet information
    * `bets:<player-id>/:...`: player bet information
* `rules/:...`: rulesets
* `algos/:...`: game algorithms and info
* `decks/:...`: card deck and shoes
* `shuffle/:...`: shuffle information


