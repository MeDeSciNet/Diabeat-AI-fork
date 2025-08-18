import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:share_plus/share_plus.dart';

class ConsultPage extends StatefulWidget {
  const ConsultPage({super.key});

  @override
  State<ConsultPage> createState() => _ConsultPageState();
}

class _ConsultPageState extends State<ConsultPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  int _period = 0;

  // null when consult failed
  bool? _waiting = true;
  late String _consultation;

  @override
  void initState() {
    _controller =
        AnimationController(vsync: this, duration: const Duration(seconds: 15))
          ..addStatusListener((status) {
            if (status == AnimationStatus.completed) {
              _period++;
              _controller
                ..reset()
                ..forward();
            }
          })
          ..addListener(() {
            setState(() {});
          })
          ..forward();

    () async {
      final (ok, data) = await request.consult(context);
      if (!mounted) return;

      _controller.stop();
      if (ok) {
        setState(() {
          _waiting = false;
          _consultation = data['response']['message']['content'];
        });
      } else {
        setState(() => _waiting = null);
      }
    }();

    super.initState();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final elapsed = (15 * (_period + _controller.value)).toInt();
    final min = util.pad2Zero(elapsed ~/ 60);
    final sec = util.pad2Zero(elapsed % 60);

    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        title: const Text('AI 健康諮詢'),
        centerTitle: true,
        actions: [
          if (_waiting == false)
            IconButton(
              onPressed: _shareConsultation,
              icon: const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: switch (_waiting) {
        true => Center(
          child: Stack(
            alignment: Alignment.center,
            children: [
              Transform.scale(
                scale: 6,
                child: CircularProgressIndicator(
                  value: _controller.value,
                  year2023: false,
                ),
              ),
              Text('$min:$sec', style: const TextStyle(fontSize: 30)),
            ],
          ),
        ),
        false => Markdown(data: _consultation),
        null => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.sms_failed_rounded,
                size: 100,
                color: Colors.redAccent,
              ),
              Text('連線失敗', style: TextStyle(fontSize: 30)),
            ],
          ),
        ),
      },
    );
  }

  void _shareConsultation() {
    SharePlus.instance.share(ShareParams(text: _consultation));
  }
}
