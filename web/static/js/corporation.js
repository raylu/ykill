window.addEvent('domready', function() {
	var corp_id = document.location.pathname.split('/').getLast();
	ykill.api('/corporation/' + corp_id, function(kills) {
		var div = $('kills');
		kills.each(function(kill) {
			var a = new Element('a', {'href': '/kill/' + kill['kill_id']});
			a.appendText(kill['kill_time']);

			a.adopt(new Element('img', {
				'src': '//image.eveonline.com/Character/' + kill['victim']['character_id'] + '_32.jpg',
				'alt': kill['victim']['character_name'],
			}));
			a.appendText(kill['victim']['character_name']);
			a.adopt(new Element('img', {
				'src': '//image.eveonline.com/Corporation/' + kill['victim']['corporation_id'] + '_32.png',
				'alt': kill['victim']['corporation_name'],
			}));
			a.appendText(kill['victim']['corporation_name']);
			if (kill['victim']['alliance_id']) {
				a.adopt(new Element('img', {
					'src': '//image.eveonline.com/Alliance/' + kill['victim']['alliance_id'] + '_32.png',
					'alt': kill['victim']['alliance_name'],
				}));
				a.appendText(kill['victim']['alliance_name']);
			}

			a.adopt(new Element('img', {
				'src': '//image.eveonline.com/Character/' + kill['final_blow']['character_id'] + '_32.jpg',
				'alt': kill['final_blow']['character_name'],
			}));
			a.appendText(kill['final_blow']['character_name']);
			a.adopt(new Element('img', {
				'src': '//image.eveonline.com/Corporation/' + kill['final_blow']['corporation_id'] + '_32.png',
				'alt': kill['final_blow']['corporation_name'],
			}));
			a.appendText(kill['final_blow']['corporation_name']);
			if (kill['final_blow']['alliance_id']) {
				a.adopt(new Element('img', {
					'src': '//image.eveonline.com/Alliance/' + kill['final_blow']['alliance_id'] + '_32.png',
					'alt': kill['final_blow']['alliance_name'],
				}));
				a.appendText(kill['final_blow']['alliance_name']);
			}

			div.adopt(a);
			div.adopt(new Element('br'));
		});
	});
});
