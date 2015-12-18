window.addEvent('domready', function() {
	'use strict';

	var kill_id = document.location.pathname.split('/').getLast();
	ykill.api('/kill/' + kill_id, function(data) {
		var kill = data['kill'];
		var victim = data['victim'];
		document.title += ' - ' + victim['character_name'] + ' - ' + victim['ship_name'];

		var table = $('victim');
		table.adopt(
			new Element('tr').adopt(
				new Element('td', {'html': 'time'}),
				new Element('td', {'html': kill['kill_time']})
			),
			new Element('tr').adopt(
				new Element('td', {'html': 'system'}),
				new Element('td', {'html': ykill.format_system(kill, true)})
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['character_id'], victim['character_name'], 'Character', 64)
				),
				new Element('td').grab(new Element('a', {
					'html': victim['character_name'], 'href': '/character/' + victim['character_id']
				}))
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['corporation_id'], victim['corporation_name'], 'Corporation', 64)
				),
				new Element('td').grab(new Element('a', {
					'html': victim['corporation_name'], 'href': '/corporation/' + victim['corporation_id']
				}))
			)
		);
		if (victim['alliance_id'])
			table.grab(new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['alliance_id'], victim['alliance_name'], 'Alliance', 64)
				),
				new Element('td').grab(new Element('a', {
					'html': victim['alliance_name'], 'href': '/alliance/' + victim['alliance_id']
				}))
			));
		if (victim['faction_id'])
			table.grab(new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['faction_id'], victim['faction_name'], 'Alliance', 64)
				),
				new Element('td', {'html': victim['faction_name']})
			));
		table.adopt(
			new Element('tr').adopt(
				new Element('td', {'html': 'total'}),
				new Element('td', {'html': ykill.format_isk(kill['cost'])})
			),
			new Element('tr').adopt(
				new Element('td', {'html': 'dropped'}),
				new Element('td', {'html': ykill.format_isk(kill['dropped'])})
			)
		);

		$('battle_report').set('href', '/kill/' + kill_id + '/battle_report');

		var items = data['items'];
		var div = $('ship');
		div.setStyle('background-image', 'url(https://image.eveonline.com/Render/' + victim['ship_type_id'] + '_256.png)');
		Object.each(data['slots'], function(num, slot) {
			var divs = $(slot).getChildren();
			for (var i = 0; i < num; i++)
				divs[i].addClass('avail');

			if (!items[slot])
				return;
			var has_charges = (['high', 'medium', 'low'].indexOf(slot) > -1);
			items[slot].each(function(item) {
				var div;
				if (has_charges && item['charge'])
					div = $('charge_' + item['flag']);
				else
					div = $('slot_' + item['flag']);
				div.setStyle('background-image', 'url(https://image.eveonline.com/Type/' + item['type_id'] + '_32.png)');
				div.grab(new Element('div', {'class': 'tooltip', 'html': item['item_name']}));
			});
		});

		var dogma = data['dogma'];
		$('ehp').appendText('EHP: ' + ykill.format_number(dogma['ehp']));
		var resist_colors = {
			'em':        '#013',
			'thermal':   '#300',
			'kinetic':   '#333',
			'explosive': '#320',
		};
		['shield', 'armor'].each(function(hp_type) {
			$(hp_type + '_hp').appendText(ykill.format_number(dogma['hp'][hp_type]));
			Object.each(dogma['resists'][hp_type], function(resist, resist_type) {
				var resist_text = (resist * 100).toFixed(1);
				div = $(hp_type + '_' + resist_type)
				div.appendText(resist_text);
				var bar_px = div.getSize().x * resist;
				var color = resist_colors[resist_type];
				div.setStyle('box-shadow', 'inset ' + bar_px + 'px 0 ' + color);
			});
		});
		$('velocity').appendText(ykill.format_number(dogma['velocity']) + ' m/s');

		var attackers = $('attackers');
		attackers.grab(new Element('tr').grab(
			new Element('td', {'class': 'attacker_type', 'colspan': 4, 'html': 'final blow'})
		));
		var total_damage = calc_total_damage(data);
		attackers.grab(attacker_row(data['final_blow'], total_damage));
		if (data['attackers'].length) {
			attackers.grab(new Element('tr').grab(
				new Element('td', {'class': 'attacker_type', 'colspan': 4, 'html': 'attackers'})
			));
			// putting this in a setTimeout(..., 100) more than doubles rendering speed in firefox
			// when there are a lot of attackers. values <= 99 don't always render everything else first
			// please don't ask me why
			setTimeout(function() {
				data['attackers'].each(function(char) {
					attackers.grab(attacker_row(char, total_damage));
				});
			}, 100);
		}

		table = $('items');
		table.adopt(
			new Element('tr').grab(
				new Element('td', {'html': 'ship', 'colspan': 4, 'class': 'slot'})
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['ship_type_id'], victim['ship_name'], 'Type', 32)
				),
				new Element('td', {'html': victim['ship_name']}),
				new Element('td'),
				new Element('td', {'html': ykill.format_isk(victim['ship_cost'])})
			)
		);
		var slots = [
			'subsystem', 'high', 'medium', 'low', 'rig', 'drone bay',
			'cargo', 'special hold', 'ship hangar', 'fleet hangar',
			'command center hold', 'planetary commodities hold', 'implant', '???'
		];
		slots.each(function(slot) {
			if (!items[slot])
				return;
			table.grab(new Element('tr').grab(
				new Element('td', {'html': slot, 'colspan': 4, 'class': 'slot'})
			));
			if (slot == 'high') {
				var highs = {'dropped': {}, 'destroyed': {}};
				items[slot].each(function(item) {
					var d = item['dropped'] ? 'dropped' : 'destroyed';
					var count = item[d];
					if (highs[d][item['type_id']])
						highs[d][item['type_id']][d] += item[d];
					else
						highs[d][item['type_id']] = item;
				});
				items[slot] = [];
				Object.each(highs, function(item_class) {
					Object.each(item_class, function(item) {
						items[slot].push(item);
					});
				});
			}
			items[slot].each(function(item) {
				var item_name = item['item_name'];
				var cost = item['cost'];
				if (item['singleton'] == 2) {
					item_name += ' (copy)';
					cost /= 1000;
				} else if (item['type_id'] == 33329 && item['flag'] == 89)
					cost = 0; // Genolution 'Auroral' AU-79 in implant slot

				['dropped', 'destroyed'].each(function(key) {
					if (!item[key])
						return;
					table.grab(new Element('tr').adopt(
						new Element('td').grab(
							ykill.portrait(item['type_id'], item['item_name'], 'Type', 32)
						),
						new Element('td', {'html': item_name}),
						new Element('td', {'html': ykill.format_number(item[key]), 'class': key}),
						new Element('td', {'html': ykill.format_isk(item[key] * cost)})
					));
				});
			});
		});
	});

	function calc_total_damage(data) {
		var total = data['final_blow']['damage'];
		data['attackers'].each(function(char) {
			total += char['damage'];
		});
		return total;
	}

	function attacker_row(char, total_damage) {
		var tr = new Element('tr');

		var td = new Element('td');
		td.grab(ykill.portrait(char['character_id'], char['character_name'], 'Character', 32));
		if (char['alliance_id'])
			td.grab(ykill.portrait(char['alliance_id'], char['alliance_name'], 'Alliance', 32));
		else
			td.grab(ykill.portrait(char['corporation_id'], char['corporation_name'], 'Corporation', 32));
		tr.grab(td);

		td = new Element('td');
		if (char['character_id'] == 0)
			td.appendText(char['character_name'] || char['ship_name']);
		else
			td.grab(new Element('a', {
				'html': char['character_name'], 'href': '/character/' + char['character_id']
			}));

		td.grab(new Element('br'));
		td.grab(new Element('a', {
			'html': char['corporation_name'], 'href': '/corporation/' + char['corporation_id']
		}));

		if (char['alliance_id']) {
			td.grab(new Element('br'));
			td.grab(new Element('a', {
				'html': char['alliance_name'], 'href': '/alliance/' + char['alliance_id']
			}));
		} else if (char['faction_id']) {
			td.grab(new Element('br'));
			td.appendText(char['faction_name']);
		}

		tr.grab(td);

		td = new Element('td').adopt(
			new Element('div').adopt(
				ykill.portrait(char['ship_type_id'], char['ship_name'], 'Type', 32),
				new Element('div', {'class': 'tooltip', 'html': char['ship_name']})
			),
			new Element('div').adopt(
				ykill.portrait(char['weapon_type_id'], char['weapon_name'], 'Type', 32),
				new Element('div', {'class': 'tooltip', 'html': char['weapon_name']})
			)
		);
		tr.grab(td);

		td = new Element('td').appendText(char['damage'].toLocaleString());
		td.grab(new Element('br'));
		var percent = char['damage'] / total_damage;
		td.appendText(percent.toLocaleString('en-US', {'style': 'percent', 'maximumFractionDigits': 1}));
		tr.grab(td);

		return tr;
	}
});
