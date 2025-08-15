import 'dart:convert';
import 'dart:developer';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/network/session.dart' as session;
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
  String? _chat;
  int _period = 0;

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
      final result = await request.chat(context);
      if (!mounted) return;

      _controller.stop();
      if (result.ok) {
        setState(() => _chat = result.data['response']['message']['content']);
      } else {
        log('consult failed');
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
          if (_chat != null)
            IconButton(
              onPressed: _shareConsultation,
              icon: const Icon(Icons.ios_share_rounded),
            ),
        ],
      ),
      body: _chat == null
          ? SizedBox.expand(
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
                  Text('$min:$sec', style: TextStyle(fontSize: 30)),
                ],
              ),
            )
          : Markdown(data: _chat!),
    );
  }

  void _shareConsultation() {
    final bytes = utf8.encode(_chat!);

    SharePlus.instance.share(
      ShareParams(
        files: [XFile.fromData(bytes)],
        fileNameOverrides: [
          '${session.username}_DiabeatConsult_${DateTime.now().toIso8601String()}.md',
        ],
      ),
    );
  }
}
