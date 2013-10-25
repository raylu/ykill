window.addEvent('domready', function() {
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
				new Element('td', {'html': ykill.format_system(kill['system_name'], kill['security'], kill['security_status'])})
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['character_id'], victim['character_name'], 'character', '_64.jpg')
				),
				new Element('td', {'html': victim['character_name']})
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['corporation_id'], victim['corporation_name'], 'corporation', '_64.png')
				),
				new Element('td', {'html': victim['corporation_name']})
			)
		);
		if (victim['alliance_id'])
			table.grab(new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['alliance_id'], victim['alliance_name'], 'alliance', '_64.png')
				),
				new Element('td', {'html': victim['alliance_name']})
			));
		if (victim['faction_id'])
			table.grab(new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['faction_id'], victim['faction_name'], 'alliance', '_64.png')
				),
				new Element('td', {'html': victim['faction_name']})
			));
		table.grab(
			new Element('tr').adopt(
				new Element('td', {'html': 'cost'}),
				new Element('td', {'html': ykill.format_isk(kill['cost'])})
			)
		);

		var items = data['items'];
		var div = $('ship');
		div.setStyle('background-image', 'url(//image.eveonline.com/render/' + victim['ship_type_id'] + '_256.png)');
		Object.each(data['slots'], function(num, slot) {
			var divs = $(slot).getChildren();
			for (var i = 0; i < num; i++)
				divs[i].addClass('avail');

			if (!items[slot])
				return;
			items[slot].each(function(item) {
				var div = $('slot_' + item['flag']);
				var bg_img = div.getStyle('background-image');
				if (bg_img == 'none')
					set_item(div, item);
				else {
					var charge_div = $('charge_' + item['flag']);
					if (item['capacity']) {
						charge_div.setStyle('background-image', bg_img);
						charge_div.grab(div.getChildren()[0]);
						set_item(div, item);
					} else {
						set_item(charge_div, item);
					}
				}
			});
		});

		table = $('attackers');
		table.grab(new Element('tr').grab(
			new Element('td', {'class': 'attacker_type', 'colspan': 4, 'html': 'final blow'})
		));
		show_attacker(table, data['final_blow']);
		if (data['attackers'].length) {
			table.grab(new Element('tr').grab(
					new Element('td', {'class': 'attacker_type', 'colspan': 4, 'html': 'attackers'})
			));
			data['attackers'].each(function(char) {
				show_attacker(table, char);
			});
		}

		table = $('items');
		table.adopt(
			new Element('tr').grab(
				new Element('td', {'html': 'ship', 'colspan': 4, 'class': 'slot'})
			),
			new Element('tr').adopt(
				new Element('td').grab(
					ykill.portrait(victim['ship_type_id'], victim['ship_name'], 'type', '_32.png')
				),
				new Element('td', {'html': victim['ship_name']}),
				new Element('td'),
				new Element('td', {'html': ykill.format_isk(victim['ship_cost'])})
			)
		);
		var slots = [
			'subsystem', 'high', 'medium', 'low', 'rig', 'drone bay',
			'cargo', 'special hold', 'ship hangar', 'fleet hangar', 'implant', '???'
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
				var type_id = item['type_id'];
				var item_name = item['item_name'];
				var item_class = item['dropped'] ? 'dropped' : 'destroyed';
				var count = item[item_class];
				var cost = item['cost'] * count;
				if (item['singleton'] == 2) {
					item_name += ' (copy)';
					cost /= 1000;
				}
				table.grab(new Element('tr').adopt(
					new Element('td').grab(
						new Element('img', {
							'src': '//image.eveonline.com/Type/' + type_id + '_32.png',
							'alt': item['item_name'],
						})
					),
					new Element('td', {'html': item_name}),
					new Element('td', {'html': count, 'class': item_class}),
					new Element('td', {'html': ykill.format_isk(cost)})
				));
			});
		});
	});

	function set_item(div, item) {
		div.setStyle('background-image', 'url(//image.eveonline.com/type/' + item['type_id'] + '_32.png)');
		div.grab(new Element('div', {'class': 'tooltip', 'html': item['item_name']}));
	}

	function show_attacker(table, char) {
		var tr = new Element('tr');

		var td = new Element('td');
		td.grab(ykill.portrait(char['character_id'], char['character_name'], 'character', '_32.jpg'));
		if (char['alliance_id'])
			td.grab(ykill.portrait(char['alliance_id'], char['alliance_name'], 'alliance', '_32.png'));
		else if (char['faction_id'])
			td.grab(ykill.portrait(char['faction_id'], char['faction_name'], 'alliance', '_32.png'));
		else
			td.grab(ykill.portrait(char['corporation_id'], char['corporation_name'], 'corporation', '_32.png'));
		tr.grab(td);

		td = new Element('td');
		td.appendText(char['character_name']);
		td.grab(new Element('br'));
		td.appendText(char['corporation_name']);
		if (char['alliance_id']) {
			td.grab(new Element('br'));
			td.appendText(char['alliance_name']);
		}
		if (char['faction_id']) {
			td.grab(new Element('br'));
			td.appendText(char['faction_name']);
		}
		tr.grab(td);

		td = new Element('td').adopt(
			ykill.portrait(char['ship_type_id'], char['ship_name'], 'type', '_32.png'),
			ykill.portrait(char['weapon_type_id'], char['weapon_name'], 'type', '_32.png')
		);
		tr.grab(td);
		tr.grab(new Element('td').appendText(char['damage'].toLocaleString()));

		table.grab(tr);
	}
});
