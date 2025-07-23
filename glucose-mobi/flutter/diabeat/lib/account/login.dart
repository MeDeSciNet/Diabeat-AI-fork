import 'package:flutter/material.dart';
import '../guest/scanner.dart';
import '../util.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  String? _emailError;
  String? _passwordError;
  bool _obscure = true;
  bool _rememberMe = true;
  bool _submitted = false;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  void _validateEmail() {
    final email = _emailController.text;

    if (email.isEmpty) {
      _emailError = '電子信箱不能為空';
    } else if (!email.contains('@')) {
      _emailError = '電子信箱格式不正確';
    } else {
      _emailError = null;
    }
  }

  void _validatePassword() {
    final password = _passwordController.text;
    _passwordError = password.isEmpty ? '密碼不能為空' : null;
  }

  @override
  Widget build(context) => Scaffold(
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
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              textInputAction: TextInputAction.next,
              decoration: InputDecoration(
                labelText: '電子信箱',
                errorText: _emailError,
                border: const OutlineInputBorder(),
              ),
              onChanged: (_) {
                if (_submitted) {
                  setState(_validateEmail);
                }
              },
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _passwordController,
              keyboardType: TextInputType.visiblePassword,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: '密碼',
                errorText: _passwordError,
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
              onChanged: (_) {
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
            FilledButton(
              onPressed: () {
                setState(() {
                  _submitted = true;
                  _validateEmail();
                  _validatePassword();
                });

                if (_emailError == null && _passwordError == null) {
                  // TODO: determine has saved host

                  DisconnectedDialog.show(context);
                }
              },
              style: BtnStyleExt.mainFilled,
              child: const Text('登入'),
            ),
          ],
        ),
      ),
    ),
  );
}
