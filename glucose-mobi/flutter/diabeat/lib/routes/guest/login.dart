import 'package:diabeat/routes/network/request.dart' as request;
import 'package:diabeat/routes/guest/auth_state.dart';
import 'package:diabeat/routes/network/session.dart' as session;
import 'package:diabeat/util.dart' as util;
import 'package:flutter/material.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  AuthState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends AuthState<LoginPage> {
  String? _passwordErr;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: util.backIconButton(context),
        actions: [util.scanIconButton(context, waiting)],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Form(
            key: formKey,
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
                buildEmailField(),
                const SizedBox(height: 20),
                TextFormField(
                  validator: passwordValidator,
                  forceErrorText: _passwordErr,
                  onSaved: (newValue) => password = newValue!,
                  keyboardType: TextInputType.visiblePassword,
                  textInputAction: TextInputAction.send,
                  obscureText: passwordObscured,
                  decoration: passwordDecoration(),
                  onChanged: (value) {
                    if (_passwordErr != null) {
                      setState(() => _passwordErr = null);
                    }
                  },
                  onFieldSubmitted: waiting
                      ? null
                      : (value) {
                          _tryLogIn();
                        },
                ),
                const Spacer(flex: 2),
                FilledButton.icon(
                  onPressed: waiting ? null : _tryLogIn,
                  style: util.filledPageButtonStyle(),
                  icon: waiting
                      ? Transform.scale(
                          scale: 0.5,
                          child: const CircularProgressIndicator(
                            year2023: false,
                          ),
                        )
                      : const Icon(Icons.login_rounded),
                  label: waiting ? const Text('登入中') : const Text('登入'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _tryLogIn() async {
    if (!formState.validate()) return;
    formState.save();
    unfocus();
    setState(() => waiting = true);

    final (ok, data) = await request.logIn(
      context,
      email: email,
      password: password,
    );
    if (!mounted) return;

    if (ok) {
      session.save(
        email: email,
        username: data['username'],
        accessToken: data['access'],
        refreshToken: data['refresh'],
      );
      Navigator.of(context).pushNamedAndRemoveUntil('/home', (route) => false);
      //
    } else {
      setState(() {
        waiting = false;

        if (data != null) {
          switch (data['non_field_errors'][0]) {
            case 'Email does not exist.':
              emailErr = 'Email 不存在';
              break;

            case 'Incorrect password.':
              _passwordErr = '密碼錯誤';
              break;
          }
        }
      });
    }
  }
}
