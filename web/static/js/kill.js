window.addEvent('domready', function() {
	var kill_id = document.location.pathname.split('/').getLast();
	ykill.api('/kill/' + kill_id, function(data) {
		var table = $('victim');
		var kill = data['kill'];
		var victim = data['victim'];
		table.adopt(
			new Element('tr').adopt(
				new Element('td', {'html': 'time'}),
				new Element('td', {'html': kill['kill_time']})
			),
			new Element('tr').adopt(
				new Element('td', {'html': 'system'}),
				new Element('td', {'html': kill['solarSystemName'] + ' (' + kill['security'].toFixed(1) + ')'})
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
		table.grab(new Element('tr').adopt(
			new Element('td').grab(
				ykill.portrait(victim['ship_type_id'], victim['ship_name'], 'type', '_64.png')
			),
			new Element('td', {'html': victim['ship_name']})
		));

		var items = data['items'];
		var div = $('ship');
		div.setStyle('background-image', 'url(//image.eveonline.com/render/' + victim['ship_type_id'] + '_256.png)');
		Object.each(data['slots'], function(num, slot) {
			var divs = $(slot).getChildren();
			for (var i = 0; i < num; i++)
				divs[i].addClass('avail');

			items[slot].each(function(item) {
				var div = $('slot_' + item['flag']);
				var bg_img = div.getStyle('background-image');
				if (bg_img == 'none')
					set_bg_item(div, item['type_id']);
				else {
					var charge_div = $('charge_' + item['flag']);
					if (item['capacity']) {
						set_bg_item(div, item['type_id']);
						charge_div.setStyle('background-image', bg_img);
					} else {
						set_bg_item(charge_div, item['type_id']);
					}
				}
			});
		});

		table = $('attackers');
		show_attacker(table, data['final_blow']);
		data['attackers'].each(function(char) {
			show_attacker(table, char);
		});

		table = $('items');
		var slots = ['subsystem', 'high', 'medium', 'low', 'rig', 'drone bay', 'cargo', 'special hold', 'implant', '???'];
		slots.each(function(slot) {
			if (!items[slot])
				return;
			table.grab(new Element('tr').grab(
				new Element('td', {'html': slot, 'colspan': 3, 'class': 'slot'})
			));
			items[slot].each(function(item) {
				var type_id = item['type_id'];
				if (type_id instanceof String)
					type_id = type_id.split(',', 2)[0];
				var count, item_class;
				if (item['dropped']) {
					count = item['dropped'];
					item_class = 'dropped';
				} else {
					count = item['destroyed'];
					item_class = 'destroyed';
				}
				table.grab(new Element('tr').adopt(
					new Element('td').grab(
						new Element('img', {
							'src': '//image.eveonline.com/Type/' + type_id + '_32.png',
							'alt': item['item_name'],
						})
					),
					new Element('td', {'html': item['item_name']}),
					new Element('td', {'html': count, 'class': item_class})
				));
			});
		});
	});

	function set_bg_item(div, type_id) {
		div.setStyle('background-image', 'url(//image.eveonline.com/type/' + type_id + '_32.png)');
	}

	function show_attacker(table, char) {
		var tr = new Element('tr');

		var td = new Element('td').adopt(
			ykill.portrait(char['character_id'], char['character_name'], 'character', '_32.jpg'),
			ykill.portrait(char['corporation_id'], char['corporation_name'], 'corporation', '_32.png')
		);
		if (char['alliance_id'])
			td.grab(ykill.portrait(char['alliance_id'], char['alliance_name'], 'alliance', '_32.png'));
		if (char['faction_id'])
			td.grab(ykill.portrait(char['faction_id'], char['faction_name'], 'alliance', '_32.png'));
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
		tr.grab(new Element('td').appendText(char['damage']));

		table.grab(tr);
	}
});
