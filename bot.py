import os
from collections.abc import Iterator
from typing import Optional, Union

import dungeons_and_trolls_client as dnt
from dotenv import load_dotenv
from dungeons_and_trolls_client.models.dungeonsandtrolls_attributes import DungeonsandtrollsAttributes
from dungeons_and_trolls_client.models.dungeonsandtrolls_character import DungeonsandtrollsCharacter
from dungeons_and_trolls_client.models.dungeonsandtrolls_coordinates import DungeonsandtrollsCoordinates
from dungeons_and_trolls_client.models.dungeonsandtrolls_game_state import DungeonsandtrollsGameState
from dungeons_and_trolls_client.models.dungeonsandtrolls_identifiers import DungeonsandtrollsIdentifiers
from dungeons_and_trolls_client.models.dungeonsandtrolls_item import DungeonsandtrollsItem
from dungeons_and_trolls_client.models.dungeonsandtrolls_item_type import DungeonsandtrollsItemType
from dungeons_and_trolls_client.models.dungeonsandtrolls_level import DungeonsandtrollsLevel
from dungeons_and_trolls_client.models.dungeonsandtrolls_map_objects import DungeonsandtrollsMapObjects
from dungeons_and_trolls_client.models.dungeonsandtrolls_monster import DungeonsandtrollsMonster
from dungeons_and_trolls_client.models.dungeonsandtrolls_skill import DungeonsandtrollsSkill
from dungeons_and_trolls_client.models.dungeonsandtrolls_skill_use import DungeonsandtrollsSkillUse
from dungeons_and_trolls_client.models.skill_target import SkillTarget
from dungeons_and_trolls_client.rest import ApiException
from pydantic import StrictFloat, StrictInt

load_dotenv()

configuration = dnt.Configuration(
    host=os.getenv("HOST"),
    api_key={'ApiKeyAuth': os.getenv("API_KEY")}
)


# Computes dot product for the given wepon and character attritbutes.
def compute_damage(skill_damage_amount: DungeonsandtrollsAttributes,
                   character_attributes: DungeonsandtrollsAttributes) -> float:
    return sum([weapon_val * getattr(character_attributes, attr_name, 0)
                for attr_name, weapon_val in skill_damage_amount.to_dict().items()
                if weapon_val])


# Chooses free weapon.
def choose_best_item(items: list[DungeonsandtrollsItem], type: DungeonsandtrollsItemType, character_attributes: DungeonsandtrollsAttributes,
                       budget: int) -> DungeonsandtrollsItem:
    current_item = None
    print("Budget: " + str(budget))
    filtered_items = filter(lambda x: x.slot == type, items)
    most_expensive_items = sorted(list(filtered_items), key=(lambda x: x.price), reverse=True)
    for item in most_expensive_items:
        item: DungeonsandtrollsItem
        #print(weapon.name + " Price: " + str(weapon.price) + " Requirements:" + weapon.requirements.to_str())
        if attributes_matches(item.requirements, character_attributes) and item.price < budget:
            current_item = item
            break
    if current_item is not None:
        print("Buying "+current_item.name)
    return current_item


def attributes_matches(required: DungeonsandtrollsAttributes, actual: DungeonsandtrollsAttributes) -> bool:
    return attribute_matches(required.strength, actual.strength) and attribute_matches(required.dexterity,
                                                                                       actual.dexterity) and attribute_matches(
        required.intelligence, actual.intelligence) and attribute_matches(required.willpower,
                                                                          actual.willpower) and attribute_matches(
        required.constitution, actual.constitution) and attribute_matches(required.life,
                                                                          actual.life) and attribute_matches(
        required.stamina, actual.stamina) and attribute_matches(required.mana, actual.mana) and attribute_matches(
        required.slash_resist, actual.slash_resist) and attribute_matches(required.pierce_resist,
                                                                          actual.pierce_resist) and attribute_matches(
        required.fire_resist, actual.pierce_resist) and attribute_matches(required.fire_resist,
                                                                          actual.fire_resist) and attribute_matches(
        required.poison_resist, actual.poison_resist) and attribute_matches(required.electric_resist,
                                                                            actual.electric_resist)


def attribute_matches(required: Optional[Union[StrictFloat, StrictInt]],
                      actual: Optional[Union[StrictFloat, StrictInt]]) -> bool:
    if required is None:
        return True
    if required is not None and actual is None:
        return False
    if required > actual:
        return False
    else:
        return True


def assign_skill_points(character: DungeonsandtrollsCharacter, api_instance: dnt.DungeonsAndTrollsApi) -> bool:
    if character.skill_points == 0:
        return False
    print("Assigning skill points")
    skill_points_partial = character.skill_points / 10
    stamina_points = character.skill_points - (skill_points_partial * 6)
    attr: DungeonsandtrollsAttributes = DungeonsandtrollsAttributes(
        stamina=stamina_points,
        strength=skill_points_partial,
        dexterity=skill_points_partial,
        constitution=skill_points_partial,
        life=skill_points_partial,
        slash_resist=skill_points_partial,
        pierce_resist=skill_points_partial
    )
    print("Assigning " + str(character.skill_points) + " skill points to " + attr.to_str())
    api_instance.dungeons_and_trolls_assign_skill_points(attr)
    return True


# Optimization function to select the best gear for the player based on budget.
def select_gear(items: list[DungeonsandtrollsItem],
                character: DungeonsandtrollsCharacter) -> DungeonsandtrollsIdentifiers:
    gear = DungeonsandtrollsIdentifiers()
    gear.ids = []
    equiped = set([equip.id for equip in character.equip])
    if len(equiped) > 0:
        return gear
    print("Selecting gear")
    budget = character.money
    item = choose_best_item(items, DungeonsandtrollsItemType.MAINHAND, character.attributes, budget)
    if item:
        gear.ids.append(item.id)
        budget = budget - item.price
    item = choose_best_item(items, DungeonsandtrollsItemType.BODY, character.attributes, budget)
    if item:
        gear.ids.append(item.id)
        budget = budget - item.price
    item = choose_best_item(items, DungeonsandtrollsItemType.HEAD, character.attributes, budget)
    if item:
        gear.ids.append(item.id)
        budget = budget - item.price
    item = choose_best_item(items, DungeonsandtrollsItemType.LEGS, character.attributes, budget)
    if item:
        gear.ids.append(item.id)
        budget = budget - item.price
    item = choose_best_item(items, DungeonsandtrollsItemType.NECK, character.attributes, budget)
    if item:
        gear.ids.append(item.id)
    return gear


# Buy the provided gear, if there is any.
def maybe_buy_gear(gear: DungeonsandtrollsIdentifiers, api_instance: dnt.DungeonsAndTrollsApi):
    if len(gear.ids) > 0:
        api_instance.dungeons_and_trolls_buy(gear)


# Check the skill cost against the character attributes.
def can_character_use_skill(skill_cost: DungeonsandtrollsAttributes,
                            character_attributes: DungeonsandtrollsAttributes) -> bool:
    for cost_attr_key, cost_attr_val in skill_cost.to_dict().items():
        if cost_attr_val and getattr(character_attributes, cost_attr_key, 0) < cost_attr_val:
            print("missing attribute " + cost_attr_key + " required: " + str(cost_attr_val) + ", have: " + str(
                getattr(character_attributes, cost_attr_key, 0)))
            return False
    return True


# Select skill that deals any damage.
def select_damage_skill(items: Iterator[DungeonsandtrollsItem],
                 character_attrs: DungeonsandtrollsAttributes) -> DungeonsandtrollsSkill:
    for item in items:
        skill: DungeonsandtrollsSkill = None
        most_damaging_skills = sorted(item.skills, key=(lambda x: compute_damage(x.damage_amount, character_attrs)), reverse=True)
        for skill in most_damaging_skills:
            can_use_skill = can_character_use_skill(skill.cost, character_attrs)
            skill.target: SkillTarget
            if skill.target != SkillTarget.CHARACTER:
                can_use_skill = False
            if can_use_skill:
                return skill
    return None

def select_heal_skill(items: Iterator[DungeonsandtrollsItem],
                 character_attrs: DungeonsandtrollsAttributes) -> DungeonsandtrollsSkill:
    for item in items:
        skill: DungeonsandtrollsSkill = None
        for skill in item.skills:
            can_use_skill = can_character_use_skill(skill.cost, character_attrs)
            skill.target: SkillTarget
            if skill.target != SkillTarget.NONE:
                can_use_skill = False
            if can_use_skill:
                return skill
    return None


# Search for a tile with stairs on it.
def find_stairs_to_next_level(game: DungeonsandtrollsGameState) -> DungeonsandtrollsCoordinates:
    level: DungeonsandtrollsLevel = (game.map.levels[0])
    for object in level.objects:
        object: DungeonsandtrollsMapObjects
        if (object.is_stairs):
            return object.position

def find_portal(game: DungeonsandtrollsGameState) -> DungeonsandtrollsCoordinates:
    level: DungeonsandtrollsLevel = (game.map.levels[0])
    for object in level.objects:
        object: DungeonsandtrollsMapObjects
        if (object.portal):
            return object.position


# Find any monster on the current level.
def find_monster(game: DungeonsandtrollsGameState) -> (DungeonsandtrollsMonster, DungeonsandtrollsCoordinates):
    level: DungeonsandtrollsLevel = (game.map.levels[0])
    for obj in level.objects:
        if not obj.monsters:
            continue
        for monster in obj.monsters:
            monster: DungeonsandtrollsMonster
            return monster, obj.position
    return None, None


# Update the monster information, e.g. position if the monster moved recently.
def update_monster(monster_id: str, game: DungeonsandtrollsGameState) -> (
        DungeonsandtrollsMonster, DungeonsandtrollsCoordinates):
    level: DungeonsandtrollsLevel = game.map.levels[0]
    for obj in level.objects:
        obj: DungeonsandtrollsMapObjects
        for monster in obj.monsters:
            monster: DungeonsandtrollsMonster
            if monster.id == monster_id:
                return monster, obj.position
    return None, None


# Compare whether two game objects are on the same tile.
def on_the_same_position(a: DungeonsandtrollsCoordinates, b: DungeonsandtrollsCoordinates) -> bool:
    return a.position_x == b.position_x and a.position_y == b.position_y


def main():
    # Enter a context with an instance of the API client
    with dnt.ApiClient(configuration) as api_client:
        # Create an instance of the API class
        api_instance = dnt.DungeonsAndTrollsApi(api_client)

        monster_pos: DungeonsandtrollsCoordinates = None
        monster: DungeonsandtrollsMonster = None

        while True:
            try:
                print("----------")
                game = api_instance.dungeons_and_trolls_game()
                print("current level", game.current_level)

                if assign_skill_points(game.character, api_instance):
                    continue

                # buy and equip items
                maybe_buy_gear(select_gear(game.shop_items, game.character), api_instance)

                #print("respawn")
                #api_instance.dungeons_and_trolls_respawn({})
                #continue

                portal_pos = find_portal(game)
                if portal_pos is not None:
                    api_instance.dungeons_and_trolls_move(portal_pos)
                    continue

                if monster_pos is None:
                    # locate any monster on current level
                    print("locating monster")
                    monster, monster_pos = find_monster(game)

                    if monster is None:
                        print("no monster on level, moving to stairs")
                        api_instance.dungeons_and_trolls_move(find_stairs_to_next_level(game))
                        continue
                else:
                    # update information for existing monster
                    monster, monster_pos = update_monster(monster.id, game)
                    if not monster:
                        continue

                character_pos: DungeonsandtrollsCoordinates = game.current_position
                if on_the_same_position(monster_pos, character_pos):
                    # select skill
                    print("selecting a skill to fight with")
                    skill = select_damage_skill(
                        # filter only MAINHAND items
                        filter(lambda x: x.slot == DungeonsandtrollsItemType.MAINHAND, game.character.equip),
                        game.character.attributes)
                    if not skill:
                        print("I can't use weapon skill, trying body skill")
                        skill = select_heal_skill(
                            filter(lambda x: x.slot == DungeonsandtrollsItemType.BODY, game.character.equip),
                            game.character.attributes)
                        print("Using body skill: "+skill.name)
                        try:
                            api_instance.dungeons_and_trolls_skill(
                                DungeonsandtrollsSkillUse(skillId=skill.id))
                        except ApiException as e:
                            print("Exception when calling DungeonsAndTrollsApi: %s\n" % e)
                        continue
                    skill_damage = compute_damage(skill.damage_amount, game.character.attributes)
                    # fight the monster
                    print("fighting with " + skill.name + "! Damage dealt: " + str(
                        skill_damage) + " monster life: " + str(monster.life_percentage) + " own life: " + str(
                        game.character.attributes.life))
                    try:
                        api_instance.dungeons_and_trolls_skill(
                            DungeonsandtrollsSkillUse(skillId=skill.id, targetId=monster.id))
                    except ApiException as e:
                        monster, monster_pos = None, None
                        continue
                else:
                    # move to the monster
                    print("moving to monster on pos: " + str(monster_pos) + ", my pos: " + str(character_pos))
                    api_instance.dungeons_and_trolls_move(monster_pos)

            except ApiException as e:
                print("Exception when calling DungeonsAndTrollsApi: %s\n" % e)


if __name__ == "__main__":
    main()
