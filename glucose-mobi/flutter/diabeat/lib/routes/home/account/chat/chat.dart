import 'dart:developer';
import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage>
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
        log('chat failed');
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
    final min = elapsed ~/ 60;
    final sec = elapsed % 60;

    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        title: const Text('智慧血糖建議'),
        centerTitle: true,
        actions: [util.shareIconButton(context)],
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
                  Text(
                    '${min.toString().padLeft(2, '0')} : ${sec.toString().padLeft(2, '0')}',
                    style: TextStyle(fontSize: 30),
                  ),
                ],
              ),
            )
          : Markdown(data: _chat!),
    );
  }
}
