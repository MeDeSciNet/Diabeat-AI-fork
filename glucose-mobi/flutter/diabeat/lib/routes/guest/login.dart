import 'package:diabeat/routes/connection/request.dart';
import 'package:diabeat/util.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();

  String? _emailErr;
  String? _passwordErr;
  bool _obscure = true;
  bool _rememberMe = true;
  bool _submitted = false;
  bool _waiting = false;
  bool _debug = true; // debug

  @override
  void initState() {
    super.initState();
    _toggleDebugSwitch(_debug);
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  void _validateEmail() {
    final email = _emailCtrl.text;

    if (email.isEmpty) {
      _emailErr = '電子信箱不能為空';
    } else if (!email.contains('@')) {
      _emailErr = '電子信箱格式不正確';
    } else {
      _emailErr = null;
    }
  }

  void _validatePassword() {
    final password = _passwordCtrl.text;
    _passwordErr = password.isEmpty ? '密碼不能為空' : null;
  }

  Future<void> _tryLogIn() async {
    setState(() {
      _submitted = true;
      _validateEmail();
      _validatePassword();
    });

    if (_emailErr != null || _passwordErr != null) return;

    setState(() => _waiting = true);

    try {
      final res = await Request.logIn(
        context,
        email: _emailCtrl.text,
        password: _passwordCtrl.text,
      );

      // log('[] access: ${res.data!['access']}');
      // log('[] refresh: ${res.data!['refresh']}');
      // log('[] user: ${res.data!['username']}');

      if (!mounted) return;
      Navigator.pop(context);
      await Navigator.pushReplacementNamed(context, '/home');
    } on DioException catch (e) {
      if (mounted) {
        await _LogInFailedDialog.show(context, e.response!.data);
      }
    } finally {
      setState(() => _waiting = false);
    }
  }

  // debug
  void _toggleDebugSwitch(bool value) {
    if (value) {
      setState(() => _debug = true);
      _emailCtrl.text = 'ray@gmail.com';
      _passwordCtrl.text = '12345678';
    } else {
      setState(() => _debug = false);
      _emailCtrl.clear();
      _passwordCtrl.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          onPressed: () {
            Navigator.pop(context);
          },
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(flex: 1),
              const Text(
                '歡迎回來 !',
                style: TextStyle(fontSize: 35),
                textAlign: TextAlign.center,
              ),
              const Spacer(flex: 1),
              TextField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: '電子信箱',
                  errorText: _emailErr,
                  border: const OutlineInputBorder(),
                ),
                onChanged: (value) {
                  if (_submitted) {
                    setState(_validateEmail);
                  }
                },
              ),
              const SizedBox(height: 20),
              TextField(
                controller: _passwordCtrl,
                keyboardType: TextInputType.visiblePassword,
                textInputAction: TextInputAction.done,
                decoration: InputDecoration(
                  labelText: '密碼',
                  errorText: _passwordErr,
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    onPressed: () {
                      setState(() => _obscure ^= true);
                    },
                    icon: _obscure
                        ? const Icon(Icons.visibility)
                        : const Icon(Icons.visibility_off),
                  ),
                ),
                obscureText: _obscure,
                onChanged: (value) {
                  if (_submitted) {
                    setState(_validatePassword);
                  }
                },
              ),
              const SizedBox(height: 20),
              CheckboxListTile(
                value: _rememberMe,
                onChanged: (value) {
                  setState(() => _rememberMe = value!);
                },
                title: const Text('記住我'),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              const Spacer(flex: 2),
              SwitchListTile(
                value: _debug,
                onChanged: _toggleDebugSwitch,
                title: const Text('Debug'),
                controlAffinity: ListTileControlAffinity.leading,
              ),
              FilledButton(
                onPressed: _waiting ? null : _tryLogIn,
                style: BtnStyleExt.mainFilled,
                child: const Text('登入'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LogInFailedDialog extends StatelessWidget {
  const _LogInFailedDialog._(this._data);
  final dynamic _data;

  static Future<void> show(BuildContext context, dynamic data) async {
    await showDialog(
      context: context,
      builder: (context) => _LogInFailedDialog._(data),
    );
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: Center(child: Text('登入失敗')),
    content: Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(_data['non_field_errors'][0], textAlign: TextAlign.center),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: () {
            Navigator.pop(context);
          },
          child: Text('OK'),
        ),
      ],
    ),
  );
}
